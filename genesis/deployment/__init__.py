import hashlib
import logging
import os
from abc import abstractmethod
from cerberus import Validator
from distutils.dir_util import copy_tree
from shutil import copyfile


class BaseDeployer(object):
    STEP = "unconfigured"
    NAME = "Unconfigured"
    DESC = "Unconfigured"

    SCHEMA = None

    # Internal configuration
    CUSTOM_POST_PROVISION_HOSTS = ['pfsense']
    LINUX_OS = ['pfsense', 'ubuntu', 'centos']
    WINDOWS_OS = ['windows']
    ALL_OS = LINUX_OS + WINDOWS_OS

    AUTOGENERATED_HEADER = [
        "#######################################",
        "# WARNING: THIS FILE IS AUTOGENERATED #",
        "# DO NOT EDIT MANUALLY                #",
        "#######################################",
        "",
    ]

    def __init__(self, step, config, args, deploy):
        self.step = step
        self.config = config
        self.args = args
        self.deploy = deploy

        if self.SCHEMA is not None:
            self.validator = Validator(self.SCHEMA, allow_unknown=True)

        self.logger = logging.getLogger(__name__)

    def validate(self):
        if self.SCHEMA is None:
            return True, []

        return self.validator.validate(self.config), self.validator.errors

    @abstractmethod
    def generate(self, data):
        pass

    @abstractmethod
    def execute(self, data):
        pass

    def _id(self, name):
        return hashlib.md5(name.encode('utf-8')).hexdigest()

    def _copy(self, src, dst):
        self.logger.debug('Copying {} -> {}'.format(src, dst))

        if os.path.isdir(src):
            copy_tree(src, dst)
        else:
            copyfile(src, dst)
