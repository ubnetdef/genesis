import logging
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
        for platform, hosts in vms.items():
            # Create a VMware connection
            self._vmware_connect(platform)

            # Fetch status on the VMs
            

            # Modify the VMs that have NICs detached

            # We're done
            self._vmware_disconnect(platform)

        return []