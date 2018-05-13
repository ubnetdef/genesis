import logging
from pyVim import connect
from pyVmomi import vim, vmodl #pylint: disable=no-name-in-module
from genesis.deployment import BaseDeployer


class VMwareNetworkFixer(BaseDeployer):
    STEP = "vmware-network-fixer"
    NAME = "VMwareNetworkFixer"
    DESC = "Meta deployer that ensures VMs deployed from VMware have NICs attached"

    def __init__(self, step, config, args, deploy):
        super().__init__(step, config, args, deploy)

        self.logger = logging.getLogger(__name__)
        self.platforms = config['platforms']

    def generate(self, data):
        # Determine which hosts utilize vmware
        vmware_hosts = []
        for host in self.deploy.deploy_hosts:
            template = self.deploy.templates[host['template']]
            platform = self.platforms[template['virt_platform']]

            if platform['type'] == 'vmware':
                vmware_hosts.append(host['id'])

        # Save this to the deployment data
        data['vmware_network_fixer_hosts'] = vmware_hosts

    def execute(self, data):
        # No CLI commands are run, however we do run commands
        if not data['vmware_network_fixer_hosts']:
            return []

        # Build a list of VMs we need to get status on
        vms = {}
        for host in self.deploy.flat_deploy:
            if host['id'] not in data['vmware_network_fixer_hosts']:
                continue

            template = self.deploy.templates[host['template']]
            platform_name = template['virt_platform']
            platform_vms = vms.get(platform_name, [])

            platform_vms.append("{datacenter}/vm/{folder}/{name}".format(**host))
            vms[platform_name] = platform_vms

        # Ensure NICs are enabled on all VMs
        for platform_name, hosts in vms.items():
            # Grab the platform config
            platform = self.platforms[platform_name]

            # Create a VMware connection
            method = connect.SmartConnect
            if 'allow_unverified_ssl' in platform and platform['allow_unverified_ssl']:
                method = connect.SmartConnectNoSSL

            self.logger.debug('Connecting to vSphere instance: %s', platform['host'])
            si = method(host=platform['host'],
                        user=platform['user'],
                        pwd=platform['pass'])

            # Modify NICs if required
            tasks = []
            for host in hosts:
                vm = si.content.searchIndex.FindByInventoryPath(host)

                # This should not happen
                if vm is None:
                    self.logger.error('Unable to find VM: %s (this should not happen)', host)
                    continue

                # Figure out NIC status
                dev_changes = []
                for dev in vm.config.hardware.device:
                    if not isinstance(dev, vim.vm.device.VirtualEthernetCard):
                        continue

                    virtual_nic_spec = vim.vm.device.VirtualDeviceSpec()
                    virtual_nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
                    virtual_nic_spec.device = dev
                    virtual_nic_spec.device.key = dev.key
                    virtual_nic_spec.device.macAddress = dev.macAddress
                    virtual_nic_spec.device.backing = dev.backing
                    virtual_nic_spec.device.wakeOnLanEnabled = dev.wakeOnLanEnabled

                    # Connect things, if needed
                    connectable = dev.connectable
                    changed = False
                    if not dev.connectable.startConnected:
                        connectable.startConnected = True
                        changed = True

                    if not dev.connectable.connected and dev.connectable.status == 'ok':
                        connectable.connected = True
                        changed = True

                    virtual_nic_spec.device.connectable = connectable

                    if changed:
                        dev_changes.append(virtual_nic_spec)

                if not dev_changes:
                    continue

                self.logger.info('The following VM required NIC changes: %s', host)
                spec = vim.vm.ConfigSpec()
                spec.deviceChange = dev_changes
                tasks.append(vm.ReconfigVM_Task(spec=spec))

            # Wait for the tasks to complete
            if tasks:
                self.logger.debug('Waiting for %d tasks to complete', len(tasks))
                self._wait_for_tasks(si, tasks)
                self.logger.debug('Tasks completed!')

            # We're done
            self.logger.debug('Disconnecting from: %s', platform['host'])
            connect.Disconnect(si)

        return []

    def _wait_for_tasks(self, si, tasks):
        """
        Source: https://github.com/vmware/pyvmomi-community-samples/blob/master/samples/tools/tasks.py

        Written by Michael Rice <michael@michaelrice.org>
        Github: https://github.com/michaelrice
        Website: https://michaelrice.github.io/
        Blog: http://www.errr-online.com/
        This code has been released under the terms of the Apache 2 licenses
        http://www.apache.org/licenses/LICENSE-2.0.html
        """
        property_collector = si.content.propertyCollector
        task_list = [str(task) for task in tasks]
        obj_specs = [vmodl.query.PropertyCollector.ObjectSpec(obj=task) for task in tasks]
        property_spec = vmodl.query.PropertyCollector.PropertySpec(type=vim.Task, pathSet=[], all=True)

        filter_spec = vmodl.query.PropertyCollector.FilterSpec()
        filter_spec.objectSet = obj_specs
        filter_spec.propSet = [property_spec]
        pcfilter = property_collector.CreateFilter(filter_spec, True)

        try:
            version, state = None, None

            while task_list:
                update = property_collector.WaitForUpdates(version)
                for filter_set in update.filterSet:
                    for obj_set in filter_set.objectSet:
                        task = obj_set.obj
                        for change in obj_set.changeSet:
                            if change.name == 'info':
                                state = change.val.state
                            elif change.name == 'info.state':
                                state = change.val
                            else:
                                continue

                            if not str(task) in task_list:
                                continue

                            if state == vim.TaskInfo.State.success:
                                task_list.remove(str(task))
                            elif state == vim.TaskInfo.State.error:
                                raise task.info.error

                version = update.version
        finally:
            if pcfilter:
                pcfilter.Destroy()
