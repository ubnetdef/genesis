from genesis.deployment.custom.pfsense import pfsenseProvision

CUSTOM_POST_PROVISION_MAPPINGS = {
    'pfsense': pfsenseProvision
}
