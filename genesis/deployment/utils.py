import json
import os
from genesis.deployment import BaseDeployer


class DeployFolder(BaseDeployer):
    STEP = "deploy-folder"
    NAME = "DeployFolder"
    DESC = "Meta deployer that handles creation of a deploy folder"

    def generate(self, data):
        # Create step_dir
        step_dir = "{}/step{}".format(self.args.output, self.step)

        # Create the directory
        self.logger.debug('Creating step directory: %s', step_dir)
        os.makedirs(step_dir)

        # Save this to the deployment data
        data['step_dir'] = step_dir

    def execute(self, data):
        return []


class CopyData(BaseDeployer):
    STEP = "copy-data"
    NAME = "CopyData"
    DESC = "Meta deployer that handles copying of data from a config file"

    SCHEMA = {
        'has_included_data': {
            'required': False,
            'type': 'boolean',
        },
        'included_copy_data': {
            'required': False,
            'dependencies': ['has_included_data'],
            'type': 'list',
            'schema': {
                'type': 'string',
            },
        },
    }

    def generate(self, data):
        # Copy any included data
        if self.config.get('has_included_data', False):
            extra_dir = os.path.dirname(os.path.realpath(self.args.config.name))

            for copydata in self.config.get('included_copy_data', []):
                src = '{}/{}'.format(extra_dir, copydata)
                dst = '{}/{}'.format(data['step_dir'], copydata)

                self._copy(src, dst)

    def execute(self, data):
        return []


class AnsibleGalaxyRoleDeploy(BaseDeployer):
    STEP = "ansible-galaxy-role-deploy"
    NAME = "AnsibleGalaxyRoleDeploy"
    DESC = "Meta deployer that handles installing ansible-galaxy roles"

    SCHEMA = {
        'ansible_galaxy_roles': {
            'required': False,
            'type': 'list',
            'schema': {
                'type': 'string',
            },
        },
    }

    def generate(self, data):
        # Create the directory
        roles_dir = "{}/global-roles".format(self.args.output)
        if not os.path.exists(roles_dir):
            self.logger.debug('Creating global ansible roles directory: %s', roles_dir)
            os.makedirs(roles_dir)

        # Save the directory to the deployment data
        data['roles_dir'] = roles_dir

    def execute(self, data):
        cmds = []

        # Read the DB
        ansible_galaxy_install_db = "{}/.{}".format(self.args.output, self.STEP)
        installed = []
        if os.path.isfile(ansible_galaxy_install_db):
            with open(ansible_galaxy_install_db) as fp:
                installed = json.load(fp)

        # Generate the install commands
        for role in self.config.get('ansible_galaxy_roles', []):
            if role in installed:
                continue

            cmds.append(['ansible-galaxy', 'install', role])
            installed.append(role)

        # Save the DB
        with open(ansible_galaxy_install_db, 'w') as fp:
            fp.write(json.dumps(installed))

        return cmds


class SetupCLIEnviron(BaseDeployer):
    STEP = "setup-cli-environ"
    NAME = "SetupCLIEnviron"
    DESC = "Sets up the CLI environ for deploys"

    def generate(self, data):
        data['cli_environ'] = dict(os.environ)
        data['cli_environ']['ANSIBLE_NOCOWS'] = '1'
        data['cli_environ']['ANSIBLE_ROLES_PATH'] = data['roles_dir']

    def execute(self, data):
        return []
