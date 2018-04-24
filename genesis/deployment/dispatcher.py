import logging
from genesis.deployment.ansible import Ansible
from genesis.deployment.postprovision import PostProvisionDispatcher
from genesis.deployment.terraform import Terraform
from genesis.deployment.utils import DeployFolder, CopyData

DEPLOYMENT_STEPS = [
	DeployFolder, Terraform, PostProvisionDispatcher, Ansible, CopyData
]

class DeployDispatcher(object):
	def __init__(self, stepnum, config, args, deploy):
		self.step = stepnum
		self.config = config
		self.args = args
		self.deploy = deploy
		self.deployers = {}
		self.deploy_data = {}

		self.logger = logging.getLogger(__name__)

		for step in DEPLOYMENT_STEPS:
			self.deployers[step.NAME] = step(stepnum, config, args, deploy)

	def run_generate(self):
		for step in DEPLOYMENT_STEPS:
			self.logger.debug('Running .generate() for {}'.format(step.NAME))
			self.deployers[step.NAME].generate(self.deploy_data)

	def run_execute(self):
		for step in DEPLOYMENT_STEPS:
			self.logger.debug('Running .execute() for {}'.format(step.NAME))
			cmds = self.deployers[step.NAME].execute(self.deploy_data)

			if cmds is None or len(cmds) == 0:
				continue

			if not isinstance(cmds, list):
				cmds = [cmds]

			for cmd in cmds:
				self.logger.debug('Running CMD: {}'.format(cmd))
