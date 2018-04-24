import argparse
import logging
import os
from datetime import datetime
from distutils.dir_util import copy_tree
from genesis import __description__
from genesis.deploy import DeployStrategy
from genesis.generators.ansible import Ansible
from genesis.generators.terraform import Terraform
from genesis.generators.postprovision import CustomPostProvision
from genesis.parser import YamlParser
from shutil import copyfile

def cli_main(base_dir=None):
	parser = argparse.ArgumentParser(description=__description__)

	output_arg_required = base_dir is None
	parser.add_argument('--config', help='Competition YAML file to deploy from', type=argparse.FileType('r'), required=True)
	parser.add_argument('--teams', help='Amount of teams to deploy the competition for', type=int, required=True)
	parser.add_argument('--output', help='Output directory for genesis. Defaults to the deploy folder in genesis.', required=output_arg_required)
	parser.add_argument('--data', help='Data directory for genesis. Defaults to the data folder in genesis.', required=output_arg_required)
	parser.add_argument('--dry-run', help='Perform a dry run only. This will not launch the competition infrastructure.', action='store_true', default=False)
	parser.add_argument('--only-deploy', help='Only deploy certain hosts. This contains the host IDs.', nargs='+')
	parser.add_argument('--start-team-number', help='Team number to start at', type=int, default=1)
	parser.add_argument('--batch-deploys', help='Batch VM deploys', type=int, default=9999)
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

	# Automagically handle "--data"
	if not output_arg_required and args.data is None:
		data_dir = "{}/data".format(base_dir)
		args.data = data_dir

		logger.debug('"--data" not configured. Setting it up to be: {}'.format(data_dir))

	# Cleanup "--only-deploy"
	if args.only_deploy is not None and \
		len(args.only_deploy) == 1 and ',' in args.only_deploy[0]:
		args.only_deploy = args.only_deploy[0].split(',')

		logger.debug('"--only-deploy" detected args passed with commas. Fixing.')

	main(logger, args)

def main(logger, args):
	# Timer
	main_start_time = datetime.now()
	logger.info('Genesis started on: {}'.format(main_start_time))

	# Ensure the output folder exists, if not create it
	if not os.path.exists(args.output):
		logger.debug('Output folder ({}) does not exist. Creating.'.format(args.output))
		os.makedirs(args.output)

	if not os.access(args.output, os.W_OK):
		raise Exception('Folder "{}" is not writable'.format(args.output))

	# Parse the config
	p = YamlParser(args)
	config = p.parse()

	# Print out some info about the config
	logger.info('Competition Config: {}'.format(config['name']))
	logger.info(config['description'])

	# Deal with max teams
	if 'max_teams' in config and args.teams > config['max_teams']:
		raise Exception('Config only allows a max of {} teams to be created'.format(config['max_teams']))

	# Deal with dependency resolution
	strategy = DeployStrategy(args, config)

	if args.dry_run:
		logger.info('Dry run enabled. Will not be running terraform and ansible.')

	for step, deploy_config in strategy.generate_steps():
		step_start_time = datetime.now()
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

		# Custom provisioners for snowflakes
		pp = CustomPostProvision(config, deploy_config)
		pp_data = pp.generate()
		if pp_data is not None:
			with open("{}/deploy-postprovision.yml".format(step_dir), 'w') as fp:
				fp.write(pp_data)

		# Generate the ansible stuff
		ansible = Ansible(config, deploy_config)
		ansible_hosts, ansible_config = ansible.generate()

		with open("{}/hosts".format(step_dir), 'w') as fp:
			fp.write(ansible_hosts)

		with open("{}/deploy-configure.yml".format(step_dir), 'w') as fp:
			fp.write(ansible_config)

		# Copy the roles over from genesis for ansible
		logger.debug('Copying: {}/ansible-roles -> {}/roles'.format(args.data, step_dir))
		copy_tree("{}/ansible-roles".format(args.data), "{}/roles".format(step_dir))

		# Copy over custom post provision stuff (hardcoded ATM)
		if pp_data is not None:
			logger.debug('Copying: {}/ansible-pfsense-provision -> {}/roles'.format(args.data, step_dir))
			copy_tree("{}/ansible-pfsense-provision".format(args.data), "{}/roles".format(step_dir))

		# Copy over included data with config, if it has any
		if config.get('has_included_data', False):
			extra_dir = os.path.dirname(os.path.realpath(args.config.name))

			for data in config.get('included_copy_data', []):
				src = '{}/{}'.format(extra_dir, data)
				dst = '{}/{}'.format(step_dir, data)

				logger.debug('Copying: {} -> {}'.format(src, dst))

				if os.path.isdir(src):
					copy_tree(src, dst)
				else:
					copyfile(src, dst)

		if not args.dry_run:
			# Run terraform

			# Run custom provisioners

			# Run ansible
			pass

		# Done
		step_run_time = datetime.now() - step_start_time
		logger.info('Deployment strategy #{} completed in {}s'.format(step, step_run_time.total_seconds()))

	# Done
	main_run_time = datetime.now() - main_start_time
	logger.info('Genesis completed in {}s'.format(main_run_time.total_seconds()))
