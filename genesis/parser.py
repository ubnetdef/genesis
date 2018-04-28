import genesis.utils as utils
import yaml
from abc import abstractmethod

class Parser(object):
	TOKEN_CALC = "!calc"

	def __init__(self, args):
		self.args = args
		self.data = {}

		self.load()

	@abstractmethod
	def load(self, file=None):
		pass

	def parse(self):
		tpl = self.data['teams_template']
		hosts = []
		teams = []

		for host_config in self.data['hosts']:
			host = self.data['hosts_defaults'].copy()
			host.update(host_config)
			hosts.append(host)

		self.data['hosts'] = hosts

		num_iterations = 0
		for x in range(self.args.start_team_number, self.args.start_team_number + self.args.teams):
			replace_tpl = tpl['variables'].copy()

			# Default variables
			replace_tpl['team'] = '{team}'
			replace_tpl['team_pad'] = '0{team}' if x < 10 else '{team}'

			# Initial replacement
			replace_tpl = utils.recursive_replace(replace_tpl, {'team': x, 'team_pad': '{:02d}'.format(x)}, num_iterations)

			# Interactive replacements
			## Calculations
			for k, v in replace_tpl.items():
				if v[:len(self.TOKEN_CALC)] != self.TOKEN_CALC:
					continue

				replace_tpl[k] = utils.calculator_eval(v[len(self.TOKEN_CALC):])

			team = {
				'team': utils.recursive_replace(tpl['name'], replace_tpl, num_iterations),
				'hosts': utils.recursive_replace(hosts, replace_tpl, num_iterations)
			}

			teams.append(team)
			num_iterations += 1

		self.data['teams'] = teams
		del self.data['teams_template']
		del self.data['hosts_defaults']

		return self.data


class YamlParser(Parser):
	def load(self, file=None):
		if file is None:
			file = self.args.config

		self.data = yaml.load(file, Loader=yaml.SafeLoader)