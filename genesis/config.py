from collections import UserDict
from cerberus import Validator
from genesis.platforms import PLATFORM_MAPPINGS


class ConfigException(Exception):
    pass


class Config(UserDict):

    SCHEMA = {
        'name': {
            'type': 'string',
            'required': True,
        },
        'description': {
            'type': 'string',
            'required': True,
        },
        'max_teams': {
            'type': 'integer',
            'min': 1,
        },
        'platforms': {
            'type': 'dict',
            'required': True,
            'valueschema': {
                'type': 'dict',
                'required': True,
                'schema': {
                    'type': {
                        'type': 'string',
                        'required': True,
                        'allowed': [x for x in PLATFORM_MAPPINGS],
                    },
                },
            },
        },
    }

    def __init__(self, config, dry_run):
        super().__init__()

        self.data = config
        self.dry_run = dry_run

        self.validate()
        self.parse()

    def validate(self):
        validator = Validator(self.SCHEMA, allow_unknown=True)
        if not validator.validate(self.data):
            raise ConfigException(validator.errors)

    def parse(self):
        # Handle platforms
        platforms = self.data['platforms'].copy()
        for platform, config in platforms.items():
            pf = PLATFORM_MAPPINGS[platform](config, self.dry_run)

            valid, errors = pf.validate()
            if not valid:
                raise ConfigException(errors)

            self.data['platforms'][platform] = pf
