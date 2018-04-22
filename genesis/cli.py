import argparse
import logging
import os
from datetime import datetime
from genesis import __description__
from genesis.deploy import DeployStrategy
from genesis.generators.ansible import Ansible
from genesis.generators.terraform import Terraform
from genesis.parser import YamlParser

def cli_main(base_dir=None):
	parser = argparse.ArgumentParser(description=__description__)

	output_arg_required = base_dir is None
	parser.add_argument('--config', help='Competition YAML file to deploy from', type=argparse.FileType('r'), required=True)
	parser.add_argument('--teams', help='Amount of teams to deploy the competition for', type=int, required=True)
	parser.add_argument('--output', help='Output directory for genesis. Defaults to the deploy folder in genesis.', required=output_arg_required)
	parser.add_argument('--dry-run', help='Perform a dry run only. This will not launch the competition infrastructure.', action='store_true', default=False)
	parser.add_argument('--only-deploy', help='Only deploy certain hosts. This contains the host IDs.', nargs='+')
	parser.add_argument('--start-team-number', help='Team number to start at', type=int, default=1)
	parser.add_argument('--debug', help='Enable debug mode', action='store_true', default=False)

	args = parser.parse_args()

	# Setup logging
	logging_level = logging.DEBUG if args.debug else logging.INFO
	logging.basicConfig(level=logging_level, format='[%(levelname)s](%(name)s): %(message)s')
	logger = logging.getLogger(__name__)

	# Automagically handle "--output"
	if not output_arg_required and args.output is None:
		config_name = os.path.basename(args.config.name)
		deploy_name = "{}-{}".format(datetime.now().strftime("%d%m%Y"), config_name.split('.')[0])
		args.output = "{}/deploy/{}".format(base_dir, deploy_name)

		logger.debug('"--output" not configured. Setting it up to be: {}'.format(args.output))

	# Cleanup "--only-deploy"
	if args.only_deploy is not None and \
		len(args.only_deploy) == 1 and ',' in args.only_deploy[0]:
		args.only_deploy = args.only_deploy[0].split(',')

		logger.debug('"--only-deploy" detected args passed with commas. Fixing.')

	main(logger, args)

def main(logger, args):
	# Ensure the output folder exists, if not create it
	if not os.path.exists(args.output):
		logger.debug('Output folder ({}) does not exist. Creating.'.format(args.output))
		os.makedirs(args.output)

	if not os.access(args.output, os.W_OK):
		raise Exception('Folder "{}" is not writable'.format(args.output))

	# Parse the config
	p = YamlParser(args)
	config = p.parse()

	# Deal with max teams
	if 'max_teams' in config and args.teams > config['max_teams']:
		raise Exception('Config only allows a max of {} teams to be created'.format(config['max_teams']))

	# Deal with dependency resolution
	strategy = DeployStrategy(args, config)

	if args.dry_run:
		logger.info('Dry run enabled. Will not be running terraform and ansible.')

	for step, deploy_config in strategy.generate_steps():
		logger.debug('Deployment strategy run #{}'.format(step))

		# Create the step directory
		step_dir = "{}/step{}".format(args.output, step)
		if not os.path.exists(step_dir):
			logger.debug('Creating step directory: {}'.format(step_dir))
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

		if not args.dry_run:
			# Run terraform

			# Run ansible
			pass

	# Done
