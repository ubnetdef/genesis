class DeployStrategy(object):
	def __init__(self, args, config):
		self.args = args
		self.config = config
		self.nodes = {}
		self.strategy = []

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

				if not has_uncompleted_deps:
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

		for step, strategy in enumerate(self.strategy):
			# Build the team config that need to be deployed
			teams = []

			for team in self.config['teams']:
				teams.append({
					'team': team['team'],
					'hosts': [x for x in team['hosts'] if x['id'] in strategy]
				})

			yield step, teams


class Node(object):
	def __init__(self, name, deps):
		self.name = name
		self.deps = deps
