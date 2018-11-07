from genesis.utils import hashid


class VMwareGenerator(object):

    def __init__(self, alias, platform, tf):
        self.alias = alias
        self.platform = platform
        self.tf = tf

        self.configured = []

    def generate_provider(self):
        unverified_ssl = False
        if 'allow_unverified_ssl' in self.platform:
            unverified_ssl = self.platform['allow_unverified_ssl']

        out = [
            'provider "vsphere" {',
            '\tuser = "{}"'.format(self.platform['user'].replace('\\', '\\\\')),
            '\tpassword = "{}"'.format(self.platform['pass']),
            '\tvsphere_server = "{}"'.format(self.platform['host']),
            '\tallow_unverified_ssl = {}'.format('true' if unverified_ssl else 'false'),
            '}',
        ]

        return '\n'.join(out)

    def generate_host(self, template, host, team):
        data = []

        if 'dc_{}'.format(host['datacenter']) not in self.configured:
            data.append(self._gen_datacenter(host['datacenter']))
            self.configured.append('dc_{}'.format(host['datacenter']))

        if 'ds_{}'.format(host['datastore']) not in self.configured:
            data.append(self._gen_datastore(host['datastore'], host['datacenter']))
            self.configured.append('ds_{}'.format(host['datastore']))

        if 'pool_{}'.format(host['resource_pool']) not in self.configured:
            data.append(self._gen_pool(host['resource_pool'], host['datacenter']))
            self.configured.append('pool_{}'.format(host['resource_pool']))

        if 'tpl_{}'.format(host['template']) not in self.configured:
            data.append(self._gen_template(template['id'], template['template'], host['datacenter']))
            self.configured.append('tpl_{}'.format(host['template']))

        for net in host['networks']:
            if 'net_{}'.format(net['adapter']) not in self.configured:
                data.append(self._gen_network(net['adapter'], host['datacenter']))
                self.configured.append('net_{}'.format(net['adapter']))

        data.append(self._gen_vm(host, template, team['team']))

        return '\n'.join(data)

    def _gen_datacenter(self, name):
        return '\n'.join([
            'data "vsphere_datacenter" "{}" {{'.format(hashid(name)),
            '\tname = "{}"'.format(name),
            '}'
        ])

    def _gen_datastore(self, name, datacenter):
        return '\n'.join([
            'data "vsphere_datastore" "{}" {{'.format(hashid(name)),
            '\tname = "{}"'.format(name),
            '\tdatacenter_id = "${{data.vsphere_datacenter.{}.id}}"'.format(hashid(datacenter)),
            '}'
        ])

    def _gen_pool(self, name, datacenter):
        return '\n'.join([
            'data "vsphere_resource_pool" "{}" {{'.format(hashid(name)),
            '\tname = "{}"'.format(name),
            '\tdatacenter_id = "${{data.vsphere_datacenter.{}.id}}"'.format(hashid(datacenter)),
            '}'
        ])

    def _gen_network(self, name, datacenter):
        return '\n'.join([
            'data "vsphere_network" "{}" {{'.format(hashid(name)),
            '\tname = "{}"'.format(name),
            '\tdatacenter_id = "${{data.vsphere_datacenter.{}.id}}"'.format(hashid(datacenter)),
            '}'
        ])

    def _gen_template(self, name, template, datacenter):
        return '\n'.join([
            'data "vsphere_virtual_machine" "{}" {{'.format(hashid(name)),
            '\tname = "{}"'.format(template),
            '\tdatacenter_id = "${{data.vsphere_datacenter.{}.id}}"'.format(hashid(datacenter)),
            '}'
        ])

    def _gen_vm(self, host, template, team):
        out = [
            'resource "vsphere_virtual_machine" "{}" {{'.format(hashid(host['name'] + team)),
            '\tname = "{}"'.format(host['name']),
            '\tfolder = "{}"'.format(host['folder']),
            '\tresource_pool_id = "${{data.vsphere_resource_pool.{}.id}}"'.format(hashid(host['resource_pool'])),
            '\tdatastore_id = "${{data.vsphere_datastore.{}.id}}"'.format(hashid(host['datastore'])),
            '\tnum_cpus = {}'.format(host['cpu']),
            '\tmemory = {}'.format(host['memory']),
            '\tguest_id = "${{data.vsphere_virtual_machine.{}.guest_id}}"'.format(hashid(host['template'])),
            '\tscsi_type = "${{data.vsphere_virtual_machine.{}.scsi_type}}"'.format(hashid(host['template']))
        ]

        if 'firmware' in host:
            out.append('\tfirmware = "{}"'.format(host['firmware']))

        # If the machine requires custom post provisioning, disable waiting for a network
        if template['os'] in self.tf.CUSTOM_POST_PROVISION_HOSTS:
            out.append('\twait_for_guest_net_routable = false')

        # Networks
        for net in host['networks']:
            out.append('\tnetwork_interface {')
            out.append('\t\tnetwork_id = "${{data.vsphere_network.{}.id}}"'.format(hashid(net['adapter'])))
            out.append('\t\tadapter_type = "${{data.vsphere_virtual_machine.{}.network_interface_types[0]}}"'.format(
                hashid(host['template'])))
            out.append('\t}')

        # Disks
        for disk in host['disks']:
            out.append('\tdisk {')
            out.append('\t\tlabel = "{}"'.format(disk['label']))

            if 'size' in disk:
                out.append('\t\tsize = {}'.format(disk['size']))
            else:
                out.append('\t\tsize = "${{data.vsphere_virtual_machine.{}.disks.0.size}}"'.format(
                    hashid(host['template'])))

            out.append('\t\tthin_provisioned = "${{data.vsphere_virtual_machine.{}.disks.0.thin_provisioned}}"'.format(
                hashid(host['template'])))
            out.append('\t}')

        # Clone
        out.append('\tclone {')
        out.append('\t\ttemplate_uuid = "${{data.vsphere_virtual_machine.{}.id}}"'.format(hashid(host['template'])))

        # Set the clone timeout to be 1 hour
        out.append('\t\ttimeout = 60')

        # Customize Section
        if template['os'] in self.tf.CAN_CUSTOMIZE_OS:
            dns_server_list = ['"{}"'.format(x) for x in host['dns-servers']]

            out.append('\t\tcustomize {')

            # Set customization timeout to be 45 minutes
            out.append('\t\t\ttimeout = 45')

            # linux_options
            if template['os'] in self.tf.LINUX_OS:
                out.append('\t\t\tlinux_options {')
                out.append('\t\t\t\thost_name = "{}"'.format(host['hostname']))
                out.append('\t\t\t\tdomain = "{}"'.format(host['domain']))
                out.append('\t\t\t}')

                # DNS (which needs to be 'global' on linux)
                out.append('\t\t\tdns_server_list = [{}]'.format(', '.join(dns_server_list)))
                out.append('\t\t\tdns_suffix_list = ["{}"]'.format(host['domain']))

            # windows_options
            if template['os'] in self.tf.WINDOWS_OS:
                out.append('\t\t\twindows_options {')
                out.append('\t\t\t\tcomputer_name = "{}"'.format(host['hostname']))
                out.append('\t\t\t\torganization_name = "genesis"')

                if 'terraform_windows' in host:
                    for k, v in host['terraform_windows'].items():

                        out.append('\t\t\t\t{} = "{}"'.format(k, v.replace('\\', '\\\\')))

                out.append('\t\t\t}')

            # network_interface
            gateway = None
            for net in host['networks']:
                ipaddr, netmask = net['ip'].split('/', 2)
                out.append('\t\t\tnetwork_interface {')
                out.append('\t\t\t\tipv4_address = "{}"'.format(ipaddr))
                out.append('\t\t\t\tipv4_netmask = {}'.format(netmask))

                # DNS for Windows
                if template['os'] in self.tf.WINDOWS_OS:
                    out.append('\t\t\t\tdns_server_list = [{}]'.format(', '.join(dns_server_list)))
                    out.append('\t\t\t\tdns_domain = "{}"'.format(host['domain']))

                out.append('\t\t\t}')

                if gateway is None or (gateway is not None and net.get('primary', False)):
                    gateway = net['gateway']

            out.append('\t\t\tipv4_gateway = "{}"'.format(gateway))

            out.append('\t\t}')

        out.append('\t}')
        out.append('}')

        return '\n'.join(out)
