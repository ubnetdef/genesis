#!/usr/bin/env python
import os
import sys
sys.path.append('../')

from genesis.cli import cli_main

if __name__ == "__main__":
	cli_main(os.path.dirname(os.path.realpath(__file__)))