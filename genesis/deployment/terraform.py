from genesis.deployment import BaseDeployer


class Terraform(BaseDeployer):
    STEP = "terraform"
    NAME = "Terraform"
    DESC = "Deploys VM resources"

    TERRAFORM_FILE = '01-provision.tf'
    TERRAFORM_PLAN = '.tfplan'

    CAN_CUSTOMIZE_OS = ['ubuntu', 'centos', 'windows']

    SUPPORTED_PLATFORMS = ['vmware']
    REGEX_IP_CIDR = '^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\/(?:[0-9]|[1-2][0-9]|3[0-2])$'
    REGEX_IP = '^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'

    SCHEMA = {
        'platforms': {
            'type': 'dict',
            'valueschema': {
                'type': 'dict',
                'schema': {
                    'type': {
                        'type': 'string',
                        'allowed': SUPPORTED_PLATFORMS,
                    },
                    'host': {
                        'type': 'string',
                    },
                    'user': {
                        'type': 'string',
                    },
                    'pass': {
                        'type': 'string',
                    },
                    'allow_unverified_ssl': {
                        'required': False,
                        'type': 'boolean',
                    },
                },
            },
        },
        'templates': {
            'type': 'list',
            'schema': {
                'type': 'dict',
                'schema': {
                    'virt_platform': {
                        'type': 'string',
                    },
                    'os': {
                        'type': 'string',
                        'allowed': BaseDeployer.ALL_OS,
                    },
                    'template': {
                        'type': 'string',
                    },
                },
            },
        },
        'hosts': {
            'type': 'list',
            'schema': {
                'type': 'dict',
                'schema': {
                    'id': {
                        'type': 'string',
                    },
                    'name': {
                        'type': 'string',
                    },
                    'domain': {
                        'type': 'string',
                    },
                    'datacenter': {
                        'type': 'string',
                    },
                    'datastore': {
                        'type': 'string',
                    },
                    'resource_pool': {
                        'type': 'string',
                    },
                    'folder': {
                        'type': 'string',
                    },
                    'template': {
                        'type': 'string',
                    },
                    'cpu': {
                        'type': 'integer',
                        'min': 1,
                    },
                    'memory': {
                        'type': 'integer',
                        'min': 128,
                    },
                    'disks': {
                        'type': 'list',
                        'schema': {
                            'type': 'dict',
                            'schema': {
                                'label': {
                                    'type': 'string',
                                },
                                'size': {
                                    'required': False,
                                    'type': 'integer',
                                    'min': 1,
                                }
                            }
                        }
                    },
                    'networks': {
                        'type': 'list',
                        'schema': {
                            'type': 'dict',
                            'schema': {
                                'adapter': {
                                    'type': 'string',
                                },
                                'ip': {
                                    'type': 'string',
                                    'regex': REGEX_IP_CIDR
                                },
                                'gateway': {
                                    'type': 'string',
                                    'regex': REGEX_IP,
                                },
                                'primary': {
                                    'required': False,
                                    'type': 'boolean',
                                },
                            },
                        },
                    },
                    'dns-servers': {
                        'type': 'list',
                        'schema': {
                            'type': 'string',
                            'regex': REGEX_IP,
                        },
                    },
                    'dependency': {
                        'required': False,
                        'type': 'list',
                        'schema': {
                            'type': 'string'
                        },
                    },
                },
            },
        },
    }

    def generate(self, data):
        # Write the terraform config
        with open("{}/{}".format(data['step_dir'], self.TERRAFORM_FILE), 'w') as fp:
            fp.write(self._generate_tf_config())

    def execute(self, data):
        return [
            ['terraform', 'init'],
            ['terraform', 'plan', '-out', self.TERRAFORM_PLAN],
            ['terraform', 'apply', self.TERRAFORM_PLAN]
        ]

    def _generate_tf_config(self):
        data = [] + self.AUTOGENERATED_HEADER

        # Setup platform
        for name, platform in self.config['platforms'].items():
            data.append(self._gen_provider(platform['user'], platform['pass'],
                                           platform['host'], platform['allow_unverified_ssl']))

        # Setup datacenters
        configured = []
        for team in self.deploy.deploy:
            for host in team['hosts']:
                if host['template'] not in self.deploy.templates:
                    raise Exception('Failed to find template for {}'.format(host['template']))

                template = self.deploy.templates[host['template']]

                if 'dc_{}'.format(host['datacenter']) not in configured:
                    data.append(self._gen_datacenter(host['datacenter']))
                    configured.append('dc_{}'.format(host['datacenter']))

                if 'ds_{}'.format(host['datastore']) not in configured:
                    data.append(self._gen_datastore(host['datastore'], host['datacenter']))
                    configured.append('ds_{}'.format(host['datastore']))

                if 'pool_{}'.format(host['resource_pool']) not in configured:
                    data.append(self._gen_pool(host['resource_pool'], host['datacenter']))
                    configured.append('pool_{}'.format(host['resource_pool']))

                if 'tpl_{}'.format(host['template']) not in configured:
                    data.append(self._gen_template(template['id'], template['template'], host['datacenter']))
                    configured.append('tpl_{}'.format(host['template']))

                for net in host['networks']:
                    if 'net_{}'.format(net['adapter']) not in configured:
                        data.append(self._gen_network(net['adapter'], host['datacenter']))
                        configured.append('net_{}'.format(net['adapter']))

                data.append(self._gen_vm(host, template, team['team']))

        return '\n'.join(data)

    def _gen_provider(self, user, passwd, server, unverified_ssl, alias=None):
        out = [
            'provider "vsphere" {',
            '\tuser = "{}"'.format(user.replace('\\', '\\\\')),
            '\tpassword = "{}"'.format(passwd),
            '\tvsphere_server = "{}"'.format(server),
            '\tallow_unverified_ssl = {}'.format('true' if unverified_ssl else 'false')
        ]

        if alias is not None:
            out.append('\talias = "{}"'.format(alias))

        out.append('}')

        return '\n'.join(out)

    def _gen_datacenter(self, name):
        return '\n'.join([
            'data "vsphere_datacenter" "{}" {{'.format(self._id(name)),
            '\tname = "{}"'.format(name),
            '}'
        ])

    def _gen_datastore(self, name, datacenter):
        return '\n'.join([
            'data "vsphere_datastore" "{}" {{'.format(self._id(name)),
            '\tname = "{}"'.format(name),
            '\tdatacenter_id = "${{data.vsphere_datacenter.{}.id}}"'.format(self._id(datacenter)),
            '}'
        ])

    def _gen_pool(self, name, datacenter):
        return '\n'.join([
            'data "vsphere_resource_pool" "{}" {{'.format(self._id(name)),
            '\tname = "{}"'.format(name),
            '\tdatacenter_id = "${{data.vsphere_datacenter.{}.id}}"'.format(self._id(datacenter)),
            '}'
        ])

    def _gen_network(self, name, datacenter):
        return '\n'.join([
            'data "vsphere_network" "{}" {{'.format(self._id(name)),
            '\tname = "{}"'.format(name),
            '\tdatacenter_id = "${{data.vsphere_datacenter.{}.id}}"'.format(self._id(datacenter)),
            '}'
        ])

    def _gen_template(self, name, template, datacenter):
        return '\n'.join([
            'data "vsphere_virtual_machine" "{}" {{'.format(self._id(name)),
            '\tname = "{}"'.format(template),
            '\tdatacenter_id = "${{data.vsphere_datacenter.{}.id}}"'.format(self._id(datacenter)),
            '}'
        ])

    def _gen_vm(self, host, template, team):
        out = [
            'resource "vsphere_virtual_machine" "{}" {{'.format(self._id(host['name'] + team)),
            '\tname = "{}"'.format(host['name']),
            '\tfolder = "{}"'.format(host['folder']),
            '\tresource_pool_id = "${{data.vsphere_resource_pool.{}.id}}"'.format(self._id(host['resource_pool'])),
            '\tdatastore_id = "${{data.vsphere_datastore.{}.id}}"'.format(self._id(host['datastore'])),
            '\tnum_cpus = {}'.format(host['cpu']),
            '\tmemory = {}'.format(host['memory']),
            '\tguest_id = "${{data.vsphere_virtual_machine.{}.guest_id}}"'.format(self._id(host['template'])),
            '\tscsi_type = "${{data.vsphere_virtual_machine.{}.scsi_type}}"'.format(self._id(host['template']))
        ]

        # If the machine requires custom post provisioning, disable waiting for a network
        if template['os'] in self.CUSTOM_POST_PROVISION_HOSTS:
            out.append('\twait_for_guest_net_routable = false')

        # Networks
        for net in host['networks']:
            out.append('\tnetwork_interface {')
            out.append('\t\tnetwork_id = "${{data.vsphere_network.{}.id}}"'.format(self._id(net['adapter'])))
            out.append('\t\tadapter_type = "${{data.vsphere_virtual_machine.{}.network_interface_types[0]}}"'.format(
                self._id(host['template'])))
            out.append('\t}')

        # Disks
        for disk in host['disks']:
            out.append('\tdisk {')
            out.append('\t\tlabel = "{}"'.format(disk['label']))

            if 'size' in disk:
                out.append('\t\tsize = {}'.format(disk['size']))
            else:
                out.append('\t\tsize = "${{data.vsphere_virtual_machine.{}.disks.0.size}}"'.format(
                    self._id(host['template'])))

            out.append('\t\tthin_provisioned = "${{data.vsphere_virtual_machine.{}.disks.0.thin_provisioned}}"'.format(
                self._id(host['template'])))
            out.append('\t}')

        # Clone
        out.append('\tclone {')
        out.append('\t\ttemplate_uuid = "${{data.vsphere_virtual_machine.{}.id}}"'.format(self._id(host['template'])))

        # Set the clone timeout to be 1 hour
        out.append('\t\ttimeout = 60')

        # Customize Section
        if template['os'] in self.CAN_CUSTOMIZE_OS:
            dns_server_list = ['"{}"'.format(x) for x in host['dns-servers']]

            out.append('\t\tcustomize {')

            # Set customization timeout to be 45 minutes
            out.append('\t\t\ttimeout = 45')

            # linux_options
            if template['os'] in self.LINUX_OS:
                out.append('\t\t\tlinux_options {')
                out.append('\t\t\t\thost_name = "{}"'.format(host['hostname']))
                out.append('\t\t\t\tdomain = "{}"'.format(host['domain']))
                out.append('\t\t\t}')

                # DNS (which needs to be 'global' on linux)
                out.append('\t\t\tdns_server_list = [{}]'.format(', '.join(dns_server_list)))
                out.append('\t\t\tdns_suffix_list = ["{}"]'.format(host['domain']))

            # windows_options
            if template['os'] in self.WINDOWS_OS:
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
                if template['os'] in self.WINDOWS_OS:
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
