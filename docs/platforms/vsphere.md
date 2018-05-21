# Platform: VMware vSphere

VMware vSphere is VMware's cloud computing virtualization platform. Currently Genesis only supports connecting to **vSphere instances**. Deployments to ESXi instances have **not** been tested, nor are immediately supported.

# Requirements
The VMware vSphere user must have permissions to the vSphere instance. Please look at the following page for additional information on required privileges: [vSphere Required Privileges Notes](https://www.terraform.io/docs/providers/vsphere/index.html#notes-on-required-privileges).

Typically, the Administrator role on the vSphere instance has been used for the deployment user.

# Deployment Requirements
Genesis deploys Virtual Machines using VMware's GuestOS Customization, which is built in to vSphere. Due to this, only a limited amount of Guest OS' are supported for Genesis. To see what Guest OS' are supported, please look at [the following page](https://partnerweb.vmware.com/programs/guestOS/guest-os-customization-matrix.pdf).

As a note, this list can be expanded thanks to [the Post Provision Dispatcher](/steps/post_provision_dispatcher). Please see that page for more information on what platforms are supported, in addition to vSphere's support matrix.

# Configuration
The following section needs to be preset in your configuration YAML file.

```yaml
platforms:
  platform_name_here:
    type: vmware 
    host: VMWARE-HOST
    user: VMWARE-USER
    pass: VMWARE-PASS

    # Optional. This will disable SSL verification
    # (typically used when you have a self signed certificate)
    allow_unverified_ssl: false
```

As a note, multiple VMware vSphere servers are supported. Simply duplicate the section `platform_name_here`.