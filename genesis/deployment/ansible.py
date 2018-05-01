import os
import subprocess
import yaml
from genesis.deployment import BaseDeployer

class Ansible(BaseDeployer):
	STEP = "ansible"
	NAME = "Ansible"
	DESC = "Post-deployment configuration of a VM"

	ANSIBLE_INVENTORY = 'hosts'
	ANSIBLE_PLAYBOOK = '99-deploy-configure.yml'
	ANSIBLE_ROLES = 'ansible-roles'

	SCHEMA = {
		'templates': {
			'type': 'list',
			'schema': {
				'type': 'dict',
				'schema': {
					'os': {
						'type': 'string',
						'allowed': BaseDeployer.ALL_OS,
					},
					'username': {
						'type': 'string',
					},
					'password': {
						'type': 'string',
					},
					'ansible_opts': {
						'required': False,
						'type': 'dict',
					},
				},
			},
		},
		'hosts': {
			'type': 'list',
			'schema': {
				'type': 'dict',
				'schema': {
					'roles': {
						'required': False,
						'type': 'list',
						'schema': {
							'type': 'dict',
							'schema': {
								'name': {
									'type': 'string',
								},
								'vars': {
									'required': False,
									'type': 'dict',
								},
							},
						},
					},
				},
			},
		},
		'role_variables': {
			'required': False,
			'type': 'dict',
			'valueschema': {
				'type': 'dict',
			},
		},
	}

	def generate(self, data):
		# Inventory
		with open("{}/{}".format(data['step_dir'], self.ANSIBLE_INVENTORY), 'w') as fp:
			fp.write(self._generate_hosts())

		# Playbook
		with open("{}/{}".format(data['step_dir'], self.ANSIBLE_PLAYBOOK), 'w') as fp:
			# Grab deploy config
			deploy_cfg = self._generate_deploy()
			deploy_out = '\n'.join(self.AUTOGENERATED_HEADER) + yaml.dump(deploy_cfg)

			# Determine if we are setting up any roles
			data["{}_has_roles".format(self.STEP)] = sum([len(x['tasks']) for x in deploy_cfg]) > 0

			# Save output
			fp.write(deploy_out)

		# Copy global roles over
		copy_ansible_flag = "{}/.{}-roles-copied".format(self.args.output, self.STEP)
		if not os.path.isfile(copy_ansible_flag):
			self._copy("{}/{}".format(self.args.data, self.ANSIBLE_ROLES), data['roles_dir'])
			open(copy_ansible_flag, 'a').close()

	def execute(self, data):
		if not data["{}_has_roles".format(self.STEP)]:
			self.logger.debug("Not running ansible, as there are no roles for any host")
			return []

		return [
			['ansible-playbook', '-i', self.ANSIBLE_INVENTORY, self.ANSIBLE_PLAYBOOK]
		]

	def _generate_hosts(self):
		groups = {}
		for host in self.deploy.flat_deploy:
			if host['id'] not in groups:
				groups[host['id']] = {'hosts': [], 'inline': []}

			# Need to grab the primary IP
			primary_ip = None
			for net in host['networks']:
				if primary_ip is None or (primary_ip is not None and net.get('primary', False)):
					primary_ip, _ = net['ip'].split('/', 2)

			inline_cfg = []
			for role in host.get('roles', []):
				if 'vars' in role:
					for key, val in role['vars'].items():
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
		vars_set_hosts = []
		for host in self.deploy.deploy_hosts:
			if host['id'] in vars_set_hosts:
				continue

			out.append('[{}:vars]'.format(host['id']))

			tpl = self.deploy.templates[host['template']]
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

			for key, value in tpl.get('ansible_opts', {}).items():
				out.append('{}="{}"'.format(key, value))

			out.append('')
			vars_set_hosts.append(host['id'])

		return '\n'.join(out)

	def _generate_deploy(self):
		out = []

		included_hosts = []
		for host in self.deploy.deploy_hosts:
			if host['id'] in included_hosts:
				continue

			out_host = {
				'hosts': host['id'],
				'tasks': [],
			}

			for role in host.get('roles', []):
				role_extra = self.config.get('role_variables', {}).get(role['name'], {})
				role_cfg = {
					'include_role': {
						'name': role['name']
					}
				}

				# Merge in the extra
				role_cfg.update(role_extra)

				out_host['tasks'].append(role_cfg)

			out.append(out_host)
			included_hosts.append(host['id'])

		return out
