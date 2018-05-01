from genesis.deployment import BaseDeployer
from genesis.deployment.custom import CUSTOM_POST_PROVISION_MAPPINGS


class PostProvisionDispatcher(BaseDeployer):
    STEP = "post-provision"
    NAME = "PostProvisionDispatcher"
    DESC = "Configures a VM when configuration during deployment is unavailable"

    def __init__(self, step, config, args, deploy):
        # Holder for any custom provisioners we have
        self.provisioners = []

        super().__init__(step, config, args, deploy)

    def generate(self, data):
        # Determine if any of our 'hosts' require custom provisioning
        templates = [x for x in self.deploy.templates.values() if x['os'] in self.CUSTOM_POST_PROVISION_HOSTS]

        if not templates:
            return None

        # Grab all the hosts that will require custom workflows
        for template in templates:
            hosts = []
            tid = template['id']

            for host in self.deploy.flat_deploy:
                if host['template'] == tid:
                    hosts.append(host)

            # Run the workflow
            if hosts:
                self.logger.debug('Calling post provisioner for {}'.format(tid))

                # Create + store the provisioner
                p = CUSTOM_POST_PROVISION_MAPPINGS[tid](self.step, self.config, self.args, self.deploy)
                self.provisioners.append(p)

                # Run generate
                data["post_provision_{}_hosts".format(tid)] = hosts
                p.generate(data)

    def execute(self, data):
        cmds = []
        for p in self.provisioners:
            cmds += p.execute(data)

        return cmds
