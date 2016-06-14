from ucsschool.importer.utils.pyhook import PyHook

class MyPreModifyHook(PyHook):
  def run(self):
    self.logger.info("***** Running pre modify hook for user {}.".format(self.import_user))
