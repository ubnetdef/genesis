import os
import yaml
from genesis.deployment import BaseDeployer

class DeployFolder(BaseDeployer):
	NAME = "DeployFolder"
	DESC = "Meta deployer that handles creation of a deploy folder"

	def generate(self, data):
		# Create step_dir
		step_dir = "{}/step{}".format(self.args.output, self.step)
		if not os.path.exists(step_dir):
			self.logger.debug('Creating step directory: {}'.format(step_dir))
			os.makedirs(step_dir)

		# Save this to the deployment data
		data['step_dir'] = step_dir

	def execute(self, data):
		return None


class CopyData(BaseDeployer):
	NAME = "CopyData"
	DESC = "Meta deployer that handles copying of data from a config file"

	def generate(self, data):
		# Copy any included data
		if self.config.get('has_included_data', False):
			extra_dir = os.path.dirname(os.path.realpath(self.args.config.name))

			for copydata in self.config.get('included_copy_data', []):
				src = '{}/{}'.format(extra_dir, copydata)
				dst = '{}/{}'.format(data['step_dir'], copydata)

				self._copy(src, dst)

	def execute(self, data):
		return None