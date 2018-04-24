import yaml
from genesis.generators import BaseGenerator

class CustomPostProvision(BaseGenerator):

	def generate(self):
		# Determine if any of our 'hosts' require custom provisioning
		templates = [x for x in self.config['templates'] if x['os'] in self.CUSTOM_POST_PROVISION_HOSTS ]

		if len(templates) == 0:
			return None

		self.logger.debug('We have {} templates that are special ({})'.format(len(templates), templates))

		# Grab all the hosts that will require custom workflows
		for template in templates:
			hosts = []

			for team in self.deploy:
				for host in team['hosts']:
					if host['template'] == template['id']:
						hosts.append(host)

			# Run the workflow
			if len(hosts) > 0:
				self.logger.debug('Calling pfsenseProvision')

				p = pfsenseProvision(self.config, [{'hosts': hosts}])
				return p.generate()

		return None


class pfsenseProvision(BaseGenerator):
	PFSENSE_PROVISION_ROLE = 'pf_provision'

	def generate(self):
		out = []

		for host in self.deploy[0]['hosts']:
			# I'm being lazy for getting the platform config, sorry.
			platform = self.config['platforms']['vmware']

			# I'm also being terrible with the gw/wan/lan/opt
			gw = host['networks'][0]['gateway']
			wan = host['networks'][0]['ip']
			lan = host['networks'][1]['ip']
			opt = host['networks'][2]['ip']

			out_host = {
				'hosts': 'localhost',
				'tasks': [
					{
						'include_role': {
							'name': self.PFSENSE_PROVISION_ROLE
						},
						'vars': {
							'vcenter_host': platform['host'],
							'vcenter_user': platform['user'],
							'vcenter_pass': platform['pass'],
							'vcenter_dc': host['datacenter'],
							'vm_folder': "/{datacenter}/vm/{folder}".format(**host),
							'vm_id': host['name'],
							'vm_user': self.templates[host['template']]['username'],
							'vm_pass': self.templates[host['template']]['password'],
							'cfg_gw': gw,
							'cfg_wan': wan,
							'cfg_lan': lan,
							'cfg_opt': opt
						}
					}
				],
			}

			out.append(out_host)

		return '\n'.join(self.AUTOGENERATED_HEADER) + yaml.dump(out)