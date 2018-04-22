Windows: Install AD
=========

Installs and sets up a basic forest for Windows Active Directory

Requirements
------------

* Windows Server

Role Variables
--------------

* domain: Domain you wish to create an Active Directory on
* netbiosname: The netbios name of your Active Directory
* adbackuppass: The backup Administrator password for AD

Dependencies
------------

N/A

Example Playbook
----------------

```
- hosts: DomainControllers
  roles:
     - windows_install_ad
     	domain: my-domain.com
     	netbiosname: MYDOMAIN
     	adbackuppass: SuperSecret2!
```

License
-------

MIT

Author Information
------------------

Based on [bjh7242/NECCDC-2017-Configs](https://github.com/bjh7242/NECCDC-2017-Configs)
