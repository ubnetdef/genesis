import logging
from pyVim import connect
from pyVmomi import vmodl  # pylint: disable=no-name-in-module
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

    def __init__(self, provider, disable_platform_check):
        super().__init__(provider, disable_platform_check)

        self.logger = logging.getLogger(__name__)

    def _validate_connection(self):
        if self.disable_platform_check:
            self.logger.debug('Disabling platform check for: %s', self.data['host'])
            return True, []

        method = connect.SmartConnect
        if 'allow_unverified_ssl' in self.data and self.data['allow_unverified_ssl']:
            method = connect.SmartConnectNoSSL

        try:
            # Connect
            self.logger.debug('Connecting to vSphere instance: %s', self.data['host'])
            service_instance = method(host=self.data['host'],
                                      user=self.data['user'],
                                      pwd=self.data['pass'])

            # Disconnect
            self.logger.debug('Connected! Disconnecting...')
            connect.Disconnect(service_instance)

            # We're good
            return True, []
        except vmodl.MethodFault as error:
            return False, ["VMware Error: {}".format(error.msg)]
        except TimeoutError:
            return False, ["Timed out connecting to vSphere instance - {}".format(self.data['host'])]
