import argparse
import os
from genesis import __description__
from genesis.deploy import DeployStrategy
from genesis.generators.ansible import Ansible
from genesis.generators.terraform import Terraform
from genesis.parser import YamlParser

def cli_main():
	parser = argparse.ArgumentParser(description=__description__)

	parser.add_argument('--config', help='Competition YAML file to deploy from', type=argparse.FileType('r'), required=True)
	parser.add_argument('--output', help='Output directory for genesis', required=True)
	parser.add_argument('--dry-run', help='Perform a dry run only. This will not launch the competition infrastructure', type=bool, default=False)
	parser.add_argument('--only-deploy', help='Only deploy certain hosts', nargs='+')
	parser.add_argument('--start-team-number', help='Team number to start at', type=int, default=1)
	parser.add_argument('--teams', help='Amount of teams to deploy the competition for', type=int, required=True)
	parser.add_argument('--debug', help='Enable debug mode', action='store_true', default=False)

	main(parser.parse_args())

def main(args):
	# Ensure the output folder exists, if not create it
	if not os.path.exists(args.output):
		os.makedirs(args.output)

	if not os.access(args.output, os.W_OK):
		raise Exception('Folder "{}" is not writable'.format(args.output))

	# Parse the config
	p = YamlParser(args)
	config = p.parse()

	# Deal with dependency resolution
	strategy = DeployStrategy(config)

	for step, deploy_config in strategy.generate_steps():
		# Create the step directory
		step_dir = "{}/step{}".format(args.output, step)
		if not os.path.exists(step_dir):
			os.makedirs(step_dir)

		# Generate the terraform stuff
		tf = Terraform(config, deploy_config)
		with open("{}/deploy.tf".format(step_dir), 'w') as fp:
			fp.write(tf.generate())

		# Generate the ansible stuff
		ansible = Ansible(config, deploy_config)
		ansible_hosts, ansible_config = ansible.generate()

		with open("{}/hosts".format(step_dir), 'w') as fp:
			fp.write(ansible_hosts)

		with open("{}/deploy.yml".format(step_dir), 'w') as fp:
			fp.write(ansible_config)

		# Copy the roles over from genesis for ansible

		# Run terraform

		# Run ansible

	# Done
