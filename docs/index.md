# What is genesis?

Genesis is a next generation cyber security competition deployment and management solution. Genesis is built to rapidly deploy large-scale competition pods through a simple [YAML](http://yaml.org/) configuration file.

# How does genesis work?

Genesis is basically a wrapper around multiple programs - with the main ones being [Terraform](https://www.terraform.io/) and [Ansible](https://www.ansible.com/). When given a competition configuration file, it will generate appropriate [Terraform HCL config files](https://www.terraform.io/docs/configuration/syntax.html), and [Ansible playbooks](https://docs.ansible.com/ansible/latest/user_guide/playbooks.html#working-with-playbooks). Genesis also contains various steps to ensure your enviroment gets deployed in a safe and reusable way.

# Getting Started

See the [getting started guide](getting_started/start) for help getting genesis up and running.