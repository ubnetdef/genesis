import logging

class DeployStrategy(object):
	def __init__(self, args, config):
		self.args = args
		self.config = config
		self.nodes = {}
		self.strategy = []

		self.logger = logging.getLogger(__name__)

		# Create a deploy strategy
		self.plan_deploy()

	def plan_deploy(self):
		# Create the nodes
		for host in self.config['hosts']:
			# Handle if we're only deploying certain hosts
			if self.args.only_deploy is not None and host['id'] not in self.args.only_deploy:
				continue

			self.nodes[host['id']] = Node(host['id'], host.get('dependency', []))

		# Keep creating strategies until we have no nodes
		while len(self.nodes) > 0:
			next_strategy = []
			for hid, node in self.nodes.items():
				has_uncompleted_deps = any(x in self.nodes for x in node.deps)

				if not has_uncompleted_deps or self.args.disable_dependency:
					next_strategy.append(hid)

			# If we have a loop, next_stretegy will be empty
			if len(next_strategy) == 0:
				raise Exception('Circular reference detected')

			# Remove the elements from the nodelist
			for hid in next_strategy:
				del self.nodes[hid]

			# Save the final strategy
			self.strategy.append(next_strategy)

	def generate_steps(self):
		if len(self.strategy) == 0:
			raise Exception('No valid strategy calculated')

		chunking_additional_steps = 0
		for step, strategy in enumerate(self.strategy):
			# Build the team config that need to be deployed
			teams = []
			vms_deployed_in_step = 0
			step_chunked = False

			for team in self.config['teams']:
				if vms_deployed_in_step >= self.args.batch_deploys:
					self.logger.debug('Deployed more than {} VMs in step #{} ({}). Chunking.'.format(self.args.batch_deploys,
						step, vms_deployed_in_step))
					self.logger.debug('Chunking steps = {}. Strategy step = {}'.format(chunking_additional_steps, step))
					step_chunked = True

					yield chunking_additional_steps + step, teams

					# Reset
					vms_deployed_in_step = 0
					chunking_additional_steps += 1
					teams = []

				hosts = [x for x in team['hosts'] if x['id'] in strategy]
				vms_deployed_in_step += len(hosts)

				teams.append({
					'team': team['team'],
					'hosts': hosts
				})

			if vms_deployed_in_step > 0:
				yield chunking_additional_steps + step, Deploy(self.config, teams)


class Deploy(object):
	def __init__(self, config, deploy):
		self.config = config
		self.deploy = deploy
		self.templates = {}
		self.template_hosts = []
		self.deploy_hosts = []
		self.flat_deploy = []

		# Build the templates
		for tpl in config['templates']:
			self.templates[tpl['id']] = tpl

		# Build a list of templates that are being deployed
		for team in deploy:
			for host in team['hosts']:
				if host['template'] not in self.template_hosts:
					self.template_hosts.append(host['template'])

				if host['id'] not in self.deploy_hosts:
					self.deploy_hosts.append(host)

				self.flat_deploy.append(host)

class Node(object):
	def __init__(self, name, deps):
		self.name = name
		self.deps = deps
