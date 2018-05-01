import logging
import os
import subprocess
import sys
from datetime import datetime
from genesis.deployment.ansible import Ansible
from genesis.deployment.postprovision import PostProvisionDispatcher
from genesis.deployment.terraform import Terraform
from genesis.deployment.utils import DeployFolder, CopyData, SetupCLIEnviron, AnsibleGalaxyRoleDeploy
from genesis.deployment.vmware import VMwareNetworkFixer

class DeployDispatcher(object):
    # Deployment objects, must be in order
    DEPLOYMENT_STEPS = [
        AnsibleGalaxyRoleDeploy, SetupCLIEnviron, DeployFolder,
        Terraform, VMwareNetworkFixer, PostProvisionDispatcher, Ansible, CopyData
    ]

    # Must be object.STEP, as we don't want more of the same object
    REQUIRED_DEPLOYMENT_STEPS = [
        AnsibleGalaxyRoleDeploy.STEP, SetupCLIEnviron.STEP, DeployFolder.STEP
    ]

    EXECUTE_LOGS_DIR = 'logs'

    def __init__(self, stepnum, config, args, deploy):
        self.step = stepnum
        self.config = config
        self.args = args
        self.deploy = deploy
        self.deployers = {}
        self.deploy_data = {}

        self.logger = logging.getLogger(__name__)

        for step in self.DEPLOYMENT_STEPS:
            self.deployers[step.NAME] = step(stepnum, config, args, deploy)

        # Handle --only-steps and --not-steps
        if args.only_steps is not None:
            remove = [x for x in self.DEPLOYMENT_STEPS if x.STEP not in args.only_steps]
        elif args.not_steps is not None:
            remove = [x for x in self.DEPLOYMENT_STEPS if x.STEP in args.not_steps]
        else:
            remove = []

        # Clean up remove (makes better logging)
        remove = [x for x in remove if x.STEP not in self.REQUIRED_DEPLOYMENT_STEPS]

        # Remove
        for step in remove:
            self.DEPLOYMENT_STEPS.remove(step)

        if remove:
            self.logger.debug('Removing the following deployment steps: %s', [x.NAME for x in remove])
            self.logger.debug('Deployment steps remaining: %s', [x.NAME for x in self.DEPLOYMENT_STEPS])

    def run_validate(self):
        errors = []

        for step in self.DEPLOYMENT_STEPS:
            valid, validator_errors = self.deployers[step.NAME].validate()
            if not valid:
                errors.append({
                    'validator': step.NAME,
                    'errors': validator_errors
                })

        if errors:
            self.logger.critical('%d deployment steps failed to pass validation', len(errors))

            for error in errors:
                self.logger.critical('%s: %s', error['validator'], error['errors'])

            raise Exception('%d deployment steps failed to pass validation', len(errors))

    def run_generate(self):
        for _, step in enumerate(self.DEPLOYMENT_STEPS):
            self.logger.debug('Running .generate() for %s', step.NAME)
            self.deployers[step.NAME].generate(self.deploy_data)

    def run_execute(self):
        # Ensure log directory exists
        logfolder = "{}/{}".format(self.args.output, self.EXECUTE_LOGS_DIR)
        if not os.path.exists(logfolder):
            self.logger.debug('Output log folder (%s) does not exist. Creating.', logfolder)
            os.makedirs(logfolder)

        # Set the ENV for the commands
        cmdenv = self.deploy_data['cli_environ']

        for stepnum, step in enumerate(self.DEPLOYMENT_STEPS):
            self.logger.debug('Running .execute() for %s', step.NAME)
            cmds = self.deployers[step.NAME].execute(self.deploy_data)

            if not isinstance(cmds, list):
                raise Exception('Deployer %s did not return proper data for execute', step.NAME)

            if cmds is None or not cmds:
                continue

            # Open output file
            logfile = "step{}-action{}-{}.log".format(self.step, stepnum, step.NAME)
            fp = open("{}/{}".format(logfolder, logfile), 'w')

            for cmd in cmds:
                self.logger.debug('Running CMD: %s', cmd)

                cmd_start_time = datetime.now()
                retcode = subprocess.call(cmd, cwd=self.deploy_data['step_dir'], env=cmdenv, stdout=fp)
                cmd_run_time = datetime.now() - cmd_start_time

                self.logger.debug('CMD completed in %fs', cmd_run_time.total_seconds())

                if retcode != 0:
                    self.logger.critical('The following CMD returned a non-zero exit code (%d)', retcode)
                    self.logger.critical(cmd)
                    sys.exit(1)
