from collections import UserDict
from cerberus import Validator


class BasePlatform(UserDict):
    NAME = "Unconfigured"

    SCHEMA = None

    # Steps to run through the validator
    VALID_STEPS = ['_validate_config', '_validate_connection']

    def __init__(self, provider, dry_run):
        super().__init__()

        self.data = provider
        self.dry_run = dry_run

        if self.SCHEMA is not None:
            self.validator = Validator(self.SCHEMA, allow_unknown=True)

    def validate(self):
        for step in self.VALID_STEPS:
            fn = getattr(self, step)

            valid, errors = fn()

            if not valid:
                return valid, errors

        return True, []

    def _validate_config(self):
        if self.SCHEMA is None:
            return True, []

        return self.validator.validate(self.data), self.validator.errors

    def _validate_connection(self):
        return True, []
