from genesis.platforms.base import BasePlatform


class VMwarePlatform(BasePlatform):

    NAME = "vmware"

    SCHEMA = {
        'host': {
            'type': 'string',
            'required': True,
        },
        'user': {
            'type': 'string',
            'required': True,
        },
        'pass': {
            'type': 'string',
            'required': True,
        },
        'allow_unverified_ssl': {
            'type': 'boolean',
        },
    }

    def _validate_connection(self):
        return True, []
