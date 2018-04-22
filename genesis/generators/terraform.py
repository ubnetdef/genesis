from genesis.generators import BaseGenerator

class Terraform(BaseGenerator):
	"""
	ATTR_MAP = {
		'templates': {
			'@for-each': {
				'id', 'type', 'family', 'template'
			}
		},
		'teams': {
			'@for-each': {
				'hosts': {
					'@for-each': {
						'id',
						'domain',        # DNS Domain, needed for customization
						'datacenter',    # VMware DC
						'datastore',     # VMware DS
						'resource_pool', # VMware Resource Pool
						'folder',        # VMware Deploy Folder
						'template',      # Template to deploy (or clone) from
						'name',          # VM name, used when deploying
						'hostname',      # VM hostname
						'cpu',
						'memory',
						'disks': {
							'@for-each': {
								'name', 'size',
							},
						},
						'nic': {
							'@for-each': {
								'id', 'adapter', 'ip', 'gateway',
							},
						},
					},
				},
			},
		},
	}
	"""

	def generate(self):
		data = []

		# Setup platform
		for name, platform in self.config['platforms'].items():
			if platform['type'] != 'vmware':
				raise Exception('Unsupported')

			data.append(self._gen_provider(platform['user'], platform['pass'],
					platform['host'], platform['allow_unverified_ssl']))

		# Setup datacenters
		configured = []
		for team in self.deploy:
			for host in team['hosts']:
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
					# Grab the template
					template = None
					for tpl in self.config['templates']:
						if tpl['id'] == host['template']:
							template = tpl
							break

					if template is None:
						raise Exception('Failed to find template for {}'.format(host['template']))

					data.append(self._gen_template(template['template'], host['datacenter']))
					configured.append('tpl_{}'.format(host['template']))

				for net in host['networks']:
					if 'net_{}'.format(net['adapter']) not in configured:
						data.append(self._gen_network(net['adapter'], host['datacenter']))
						configured.append('net_{}'.format(net['adapter']))

				data.append(self._gen_vm(host, template))

		return '\n'.join(data)

	def _gen_provider(self, user, passwd, server, unverified_ssl, alias=None):
		out = [
			'provider "vsphere" {',
			'\tuser = "{}"'.format(user),
			'\tpassword = "{}"'.format(passwd),
			'\tvsphere_server = "{}"'.format(server),
			'\tallow_unverified_ssl = {}'.format(unverified_ssl)
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

	def _gen_template(self, name, datacenter):
		return '\n'.join([
			'data "vsphere_virtual_machine" "{}" {{'.format(self._id(name)),
			'\tname = "{}"'.format(name),
			'\tdatacenter_id = "${{data.vsphere_datacenter.{}.id}}"'.format(self._id(datacenter)),
			'}'
		])

	def _gen_vm(self, host, template):
		out = [
			'resource "vsphere_virtual_machine" "{}" {{'.format(self._id(host['name'])),
			'\tname = "{}"'.format(host['name']),
			'\tfolder = "{}"'.format(host['folder']),
			'\tresource_pool_id = "${{data.vsphere_resource_pool.{}.id}}"'.format(self._id(host['resource_pool'])),
			'\tdatastore_id = "${{data.vsphere_datastore.{}.id}}"'.format(self._id(host['datastore'])),
			'\tnum_cpus = {}'.format(host['cpu']),
			'\tmemory = {}'.format(host['memory']),
			'\tguest_id = "${{data.vsphere_virtual_machine.{}.guest_id}}"'.format(self._id(host['template'])),
			'\tscsi_type = "${{data.vsphere_virtual_machine.{}.scsi_type}}"'.format(self._id(host['template']))
		]

		# Networks
		for net in host['networks']:
			out.append('\tnetwork_interface {')
			out.append('\t\tnetwork_id = "${{data.vsphere_network.{}.id}}"'.format(self._id(net['adapter'])))
			out.append('\t\tadapter_type = "${{data.vsphere_virtual_machine.{}.network_interface_types[0]}}"'.format(self._id(host['template'])))
			out.append('\t}')

		# Disks
		for disk in host['disks']:
			out.append('\tdisk {')
			out.append('\t\tlabel = "{}"'.format(disk['label']))
			out.append('\t\tsize = '.format(disk['size']))
			out.append('\t\tthin_provisioned = "${{data.vsphere_virtual_machine.{}.disks.0.thin_provisioned}}"'.format(self._id(host['template'])))
			out.append('\t}')

		# Clone
		out.append('\tclone {')
		out.append('\t\ttemplate_uuid = "${{data.vsphere_virtual_machine.{}.id}}"'.format(self._id(host['template'])))

		# Customize Section
		if template['os'] in self.CAN_CUSTOMIZE_OS:
			out.append('\t\tcustomize {')

			## linux_options
			if template['os'] in self.LINUX_OS:
				out.append('\t\t\tlinux_options {')
				out.append('\t\t\t\thost_name = "{}"'.format(host['hostname']))
				out.append('\t\t\t\tdomain = "{}"'.format(host['domain']))
				out.append('\t\t\t}')

			## windows_options
			if template['os'] in self.WINDOWS_OS:
				out.append('\t\t\twindows_options {')
				out.append('\t\t\t\tcomputer_name = "{}"'.format(host['hostname']))
				out.append('\t\t\t\torganization_name = "genesis"')
				out.append('\t\t\t}')

			## network_interface
			gateway = None
			for net in host['networks']:
				ipaddr, netmask = net['ip'].split('/', 2)
				out.append('\t\t\tnetwork_interface {')
				out.append('\t\t\t\tipv4_address = "{}"'.format(ipaddr))
				out.append('\t\t\t\tipv4_netmask = {}'.format(netmask))
				out.append('\t\t\t}')

				if gateway is None or (gateway is not None and net.get('primary', False)):		
					gateway = net['gateway']

			out.append('\t\t\tipv4_gateway = "{}"'.format(gateway))

			out.append('\t\t}')

		out.append('\t}')
		out.append('}')

		return '\n'.join(out)