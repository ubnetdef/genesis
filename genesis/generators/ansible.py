import yaml
from genesis.generators import BaseGenerator

class Ansible(BaseGenerator):
	"""
	ATTR_MAP = {
		'templates': {
			'@for-each': {
				'username', 'password',
			},
		},
		'teams': {
			'@for-each': {
				'hosts': {
					'@for-each': {
						'nics': {
							'@for-each': {
								'ip',
							},
						},
						'roles'
					},
				},
			},
		},
	}
	"""

	def generate(self):
		# Return a tuple
		return self._generate_hosts(), self._generate_deploy()

	def _generate_hosts(self):
		groups = {}
		for team in self.deploy:
			for host in team['hosts']:
				if host['id'] not in groups:
					groups[host['id']] = {'hosts': [], 'inline': []}

				# Need to grab the primary IP
				primary_ip = None
				for net in host['networks']:
					if primary_ip is None or (primary_ip is not None and net.get('primary', False)):
						primary_ip, _ = net['ip'].split('/', 2)

				inline_cfg = []
				for role_name, role_config in host.get('roles', {}).items():
					if role_config is not None:
						for key, val in role_config.items():
							inline_cfg.append('{}="{}"'.format(key, val))

				groups[host['id']]['hosts'].append(primary_ip)
				groups[host['id']]['inline'].append(inline_cfg)

		# Build the ini file
		out = [] + self.AUTOGENERATED_HEADER

		for gid, cfg in groups.items():
			out.append('[{}]'.format(gid))
			for i, ip in enumerate(cfg['hosts']):
				out.append('{}\t{}'.format(ip, ' '.join(cfg['inline'][i])))
			out.append('')

		# Build the connection variables
		for host in self.deploy[0]['hosts']:
			out.append('[{}:vars]'.format(host['id']))

			tpl = self.templates[host['template']]
			if tpl['os'] in self.LINUX_OS:
				out.append('ansible_user="{}"'.format(tpl['username']))
				out.append('ansible_ssh_pass="{}"'.format(tpl['password']))
				out.append('ansible_become_pass="{}"'.format(tpl['password']))
				out.append('ansible_ssh_common_args="-o StrictHostKeyChecking=no"')
			elif tpl['os'] in self.WINDOWS_OS:
				out.append('ansible_connection=winrm')
				out.append('ansible_port=5985')
				out.append('ansible_user="{}"'.format(tpl['username']))
				out.append('ansible_password="{}"'.format(tpl['password']))
			else:
				raise Exception('Unknown OS: {}'.format(tpl['os']))

			out.append('')

		return '\n'.join(out)

	def _generate_deploy(self):
		out = []

		for host in self.deploy[0]['hosts']:
			out_host = {
				'hosts': host['id'],
				'tasks': [],
			}

			for role_name, role_config in host.get('roles', {}).items():
				role_vars = self.config.get('role_variables', {}).get(role_name, {})

				out_host['tasks'].append({
					'include_role': {
						'name': role_name
					},
					'vars': role_vars
				})

			out.append(out_host)

		return '\n'.join(self.AUTOGENERATED_HEADER) + yaml.dump(out)
