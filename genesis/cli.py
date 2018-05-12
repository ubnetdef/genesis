import argparse
import logging
import os
import sys
from datetime import datetime
from shutil import rmtree
from genesis import __description__
from genesis.config import Config
from genesis.deploy import DeployStrategy
from genesis.deployment.dispatcher import DeployDispatcher
from genesis.parser import YamlParser
from genesis.utils import fail


def cli_main(base_dir=None):
    parser = argparse.ArgumentParser(description=__description__)

    output_arg_required = base_dir is None

    # Required commands
    parser.add_argument('--config', help='Competition YAML file to deploy from',
                        type=argparse.FileType('r'), required=True)
    parser.add_argument('--teams', help='Amount of teams to deploy the competition for', type=int,
                        required=True)
    parser.add_argument('--output',
                        help='Output folder for genesis. Defaults to the deploy folder in genesis',
                        required=output_arg_required)
    parser.add_argument('--data', help='Data folder for genesis. Defaults to the data folder in genesis',
                        required=output_arg_required)

    # Limit commands
    g = parser.add_mutually_exclusive_group()
    g.add_argument('--only-steps', help='Run certain deployment steps', nargs='+')
    g.add_argument('--not-steps', help='Do not run these deployment steps', nargs='+')

    parser.add_argument('--only-deploy', help='Only deploy certain hosts. This contains the host IDs', nargs='+')
    parser.add_argument('--start-team-number', help='Team number to start at', type=int, default=1)

    # Flags
    parser.add_argument('--remove-output-folder',
                        help='Automatically remove output folder, if it exists', action='store_true', default=False)
    parser.add_argument('--disable-dependency', help='Disable dependency resolution',
                        action='store_true', default=False)
    parser.add_argument('--batch-deploys', help='Number to batch VM deploys to per step', type=int, default=9999)
    parser.add_argument('--dry-run', help='Perform a dry run only. This will not launch the competition infrastructure',
                        action='store_true', default=False)
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

        logger.debug('"--output" not configured. Setting it up to be: %s', args.output)

    # Automagically handle "--data"
    if not output_arg_required and args.data is None:
        data_dir = "{}/data".format(base_dir)
        args.data = data_dir

        logger.debug('"--data" not configured. Setting it up to be: %s', data_dir)

    # Cleanup "--only-deploy"
    if args.only_deploy is not None and \
            len(args.only_deploy) == 1 and ',' in args.only_deploy[0]:
        args.only_deploy = args.only_deploy[0].split(',')

        logger.debug('"--only-deploy" detected args passed with commas. Fixing.')

    # Cleanup "--only-steps"
    if args.only_steps is not None and \
            len(args.only_steps) == 1 and ',' in args.only_steps[0]:
        args.only_steps = args.only_steps[0].split(',')

        logger.debug('"--only-steps" detected args passed with commas. Fixing.')

    # Cleanup "--not-steps"
    if args.not_steps is not None and \
            len(args.not_steps) == 1 and ',' in args.not_steps[0]:
        args.not_steps = args.not_steps[0].split(',')

        logger.debug('"--not-steps" detected args passed with commas. Fixing.')

    # Expand paths
    args.output = os.path.expanduser(args.output)
    args.data = os.path.expanduser(args.data)

    main(logger, args)


def main(logger, args):
    # Timer
    main_start_time = datetime.now()
    logger.info('Genesis started on: %s', main_start_time)

    # Ensure the output folder does not exist (or is not empty), otherwise bad thingsTM will happen
    if os.path.exists(args.output) and os.listdir(args.output):
        if not args.remove_output_folder:
            logger.critical('Output folder (%s) already exists. Please choose another folder name', args.output)
            sys.exit(1)

        # Remove the folder
        logger.info('Removing already existing output folder - %s', args.output)
        rmtree(args.output)

    if not os.path.exists(args.output):
        logger.debug('Creating output folder - %s', args.output)
        os.makedirs(args.output)

    if not os.access(args.output, os.W_OK):
        logger.critical('Folder "%s" is not writable', args.output)
        sys.exit(1)

    # Parse the config
    try:
        p = YamlParser(args)
        raw_config = p.parse()
    except Exception as e:
        logger.critical('Error in parsing YAML: %s', e)
        fail(e, args.debug)

    # Create the config
    try:
        config = Config(raw_config, args.dry_run)
    except Exception as e:
        logger.critical('Error in config file: %s', e)
        fail(e, args.debug)

    # Print out some info about the config
    logger.info('Competition Config: %s', config['name'])
    logger.info(config['description'])

    # Deal with max teams
    if 'max_teams' in config and args.teams > config['max_teams']:
        logger.critical('Config only allows a max of %d teams to be created', config['max_teams'])
        sys.exit(1)

    # Deal with dependency resolution
    strategy = DeployStrategy(args, config)

    if args.dry_run:
        logger.info('Dry run enabled. Will not be executing the deployment.')

    for step, deploy_config in strategy.generate_steps():
        step_start_time = datetime.now()
        logger.info('Deployment strategy run #%d', step)

        dispatcher = DeployDispatcher(step, config, args, deploy_config)

        try:
            dispatcher.run_validate()
        except Exception as e:
            # Logger should already have printed it our to logger.critical
            fail(e, args.debug)

        try:
            dispatcher.run_generate()
        except Exception as e:
            logger.critical('Fatal error when generating: %s', e)
            fail(e, args.debug)

        if not args.dry_run:
            try:
                dispatcher.run_execute()
            except Exception as e:
                logger.critical('Fatal error when executing: %s', e)
                fail(e, args.debug)

        # Done
        step_run_time = datetime.now() - step_start_time
        logger.info('Deployment strategy #%d completed in %fs', step, step_run_time.total_seconds())

    # Done
    main_run_time = datetime.now() - main_start_time
    logger.info('Genesis completed in %fs', main_run_time.total_seconds())
