import logging
import os
import subprocess
import sys
from datetime import datetime
from genesis.deployment.ansible import Ansible
from genesis.deployment.postprovision import PostProvisionDispatcher
from genesis.deployment.terraform import Terraform
from genesis.deployment.utils import DeployFolder, CopyData

DEPLOYMENT_STEPS = [
	DeployFolder, Terraform, PostProvisionDispatcher, Ansible, CopyData
]

class DeployDispatcher(object):
	EXECUTE_LOGS_DIR = 'logs'

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
		# Ensure log directory exists
		logfolder = "{}/{}".format(self.args.output, self.EXECUTE_LOGS_DIR)
		if not os.path.exists(logfolder):
			self.logger.debug('Output log folder ({}) does not exist. Creating.'.format(logfolder))
			os.makedirs(logfolder)

		for step in DEPLOYMENT_STEPS:
			self.logger.debug('Running .execute() for {}'.format(step.NAME))
			cmds = self.deployers[step.NAME].execute(self.deploy_data)

			if not isinstance(cmds, list):
				raise Exception('Deployer {} did not return proper data for execute'.format(step.NAME))

			if cmds is None or len(cmds) == 0:
				continue

			# Open output file
			logfile = "step{}-{}.log".format(self.step, step.NAME)
			fp = open("{}/{}".format(logfolder, logfile), 'w')

			for cmd in cmds:
				self.logger.debug('Running CMD: {}'.format(cmd))

				cmd_start_time = datetime.now()
				retcode = subprocess.call(cmd, cwd=self.deploy_data['step_dir'], env=os.environ, stdout=fp)
				cmd_run_time = datetime.now() - cmd_start_time

				self.logger.debug('CMD completed in {}s'.format(cmd_run_time.total_seconds()))

				if retcode != 0:
					self.logger.critical('The following CMD returned a non-zero exit code ({})'.format(retcode))
					self.logger.critical(cmd)
					sys.exit(1)
