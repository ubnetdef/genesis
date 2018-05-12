import logging
from genesis.deployment import BaseDeployer
from genesis.deployment.terraform.vmware import VMwareGenerator


class Terraform(BaseDeployer):
    STEP = "terraform"
    NAME = "Terraform"
    DESC = "Deploys VM resources"

    TERRAFORM_FILE = '01-provision-{}.tf'
    TERRAFORM_PLAN = '.tfplan'

    CAN_CUSTOMIZE_OS = ['ubuntu', 'centos', 'windows']

    TERRAFORM_GENERATORS = {
        'vmware': VMwareGenerator
    }

    # pylint: disable=anomalous-backslash-in-string
    REGEX_IP_CIDR = '^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'\
        '\/(?:[0-9]|[1-2][0-9]|3[0-2])$'

    # pylint: disable=anomalous-backslash-in-string
    REGEX_IP = '^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'

    SCHEMA = {
        'templates': {
            'type': 'list',
            'required': True,
            'schema': {
                'type': 'dict',
                'required': True,
                'schema': {
                    'virt_platform': {
                        'type': 'string',
                        'required': True,
                    },
                    'os': {
                        'type': 'string',
                        'allowed': BaseDeployer.ALL_OS,
                        'required': True,
                    },
                    'template': {
                        'type': 'string',
                        'required': True,
                    },
                },
            },
        },
        'hosts': {
            'type': 'list',
            'required': True,
            'schema': {
                'type': 'dict',
                'required': True,
                'schema': {
                    'id': {
                        'type': 'string',
                        'required': True,
                    },
                    'name': {
                        'type': 'string',
                        'required': True,
                    },
                    'domain': {
                        'type': 'string',
                        'required': True,
                    },
                    'datacenter': {
                        'type': 'string',
                        'required': True,
                    },
                    'datastore': {
                        'type': 'string',
                        'required': True,
                    },
                    'resource_pool': {
                        'type': 'string',
                        'required': True,
                    },
                    'folder': {
                        'type': 'string',
                        'required': True,
                    },
                    'template': {
                        'type': 'string',
                        'required': True,
                    },
                    'cpu': {
                        'type': 'integer',
                        'required': True,
                        'min': 1,
                    },
                    'memory': {
                        'type': 'integer',
                        'required': True,
                        'min': 128,
                    },
                    'disks': {
                        'type': 'list',
                        'required': True,
                        'schema': {
                            'type': 'dict',
                            'required': True,
                            'schema': {
                                'label': {
                                    'type': 'string',
                                    'required': True,
                                },
                                'size': {
                                    'type': 'integer',
                                    'min': 1,
                                }
                            }
                        }
                    },
                    'networks': {
                        'type': 'list',
                        'required': True,
                        'schema': {
                            'type': 'dict',
                            'required': True,
                            'schema': {
                                'adapter': {
                                    'type': 'string',
                                    'required': True,
                                },
                                'ip': {
                                    'type': 'string',
                                    'required': True,
                                    'regex': REGEX_IP_CIDR
                                },
                                'gateway': {
                                    'type': 'string',
                                    'required': True,
                                    'regex': REGEX_IP,
                                },
                                'primary': {
                                    'type': 'boolean',
                                },
                            },
                        },
                    },
                    'dns-servers': {
                        'type': 'list',
                        'required': True,
                        'schema': {
                            'type': 'string',
                            'required': True,
                            'regex': REGEX_IP,
                        },
                    },
                    'dependency': {
                        'type': 'list',
                        'schema': {
                            'type': 'string',
                            'required': True,
                        },
                    },
                },
            },
        },
    }

    def __init__(self, step, config, args, deploy):
        super().__init__(step, config, args, deploy)

        self.generators = {}
        self.logger = logging.getLogger(__name__)

    def validate(self):
        # Parent validate
        valid, errors = super().validate()
        if not valid:
            return valid, errors

        # Ensure we have generators for Terraform
        for name, platform in self.config['platforms'].items():
            if platform['type'] not in self.TERRAFORM_GENERATORS:
                raise Exception('Unable to provision type {}'.format(platform['type']))

            self.generators[name] = self.TERRAFORM_GENERATORS[platform['type']](name, platform, self)

        # We're good
        return True, []

    def generate(self, data):
        # Grab the terraform config
        config = self._generate_tf_config()

        for name, cfg in config.items():
            self.logger.debug('Generating terraform file for provider %s (%s)',
                              name, self.TERRAFORM_FILE.format(name))

            with open("{}/{}".format(data['step_dir'], self.TERRAFORM_FILE.format(name)), 'w') as fp:
                fp.write('\n'.join(cfg))

    def execute(self, data):
        return [
            ['terraform', 'init'],
            ['terraform', 'plan', '-out', self.TERRAFORM_PLAN],
            ['terraform', 'apply', self.TERRAFORM_PLAN]
        ]

    def _generate_tf_config(self):
        tfconfig = {}

        # Generate the config(s)
        for team in self.deploy.deploy:
            for host in team['hosts']:
                if host['template'] not in self.deploy.templates:
                    raise Exception('Failed to find template for {}'.format(host['template']))

                template = self.deploy.templates[host['template']]
                platform = template['virt_platform']

                # Call the generator to create this bad boy up
                if platform not in tfconfig:
                    tfconfig[platform] = [] + self.AUTOGENERATED_HEADER
                    tfconfig[platform].append(self.generators[platform].generate_provider())

                tfconfig[platform].append(self.generators[platform].generate_host(template, host, team))

        return tfconfig
