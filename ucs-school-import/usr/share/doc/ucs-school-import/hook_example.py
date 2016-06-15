from ucsschool.importer.utils.pyhook import PyHook


class MyHook(PyHook):
	def run(self):
		self.logger.info("Running a %s-%s hook for %s.", self.when, self.action, self.user)
