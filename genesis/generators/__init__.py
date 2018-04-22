import hashlib
from abc import abstractmethod

class BaseGenerator(object):
	ATTR_MAP = {}

	LINUX_OS = ['freebsd', 'ubuntu', 'centos']
	WINDOWS_OS = ['windows']
	CAN_CUSTOMIZE_OS = ['ubuntu', 'centos', 'windows']

	def __init__(self, config, deploy):
		self.config = config
		self.deploy = deploy

	def validate(self):
		return True

	@abstractmethod
	def generate(self):
		pass

	def _id(self, name):
		return hashlib.md5(name.encode('utf-8')).hexdigest()
