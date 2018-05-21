# Getting Started with Genesis

## Genesis Requirements
Genesis requires the following programs to be installed:

* python3 (and pip)
* [Terraform](https://www.terraform.io/intro/getting-started/install.html)
* [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)

## Getting Genesis
Currently, you can only get Genesis via the command-line tool `git`, against the master branch. In the future, Genesis will publish versions on GitHub's releases page.

### Via Git
First, ensure you have `git` installed. Then, go to a directory you wish to store Genesis in. From there, run the following command:

```bash
git clone https://github.com/ubnetdef/genesis && cd genesis
```

Congrats, you have installed genesis!

## Installing Genesis' Requirements
Genesis requires a few other packages to be installed via pip. You can install the packages by running the following, from Genesis' directory:

```bash
pip install -r requirements.txt
```

As a note, it is **highly recommended** that you install Genesis within a [Python Virtual Enviroment](https://docs.python.org/3/library/venv.html). Typically, the following commands will work if you wish to create a virtual enviroment. You will need to run this **before** running the above command.

```bash
python3 -m venv venv && source venv/bin/activate
```

## You're done!
Assuming everything above has sucessfully ran, you installed Genesis! To run Genesis, simply type:

```bash
./genesis.py -h
```
