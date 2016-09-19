from ucsschool.importer.utils.user_pyhook import UserPyHook


class MyHook(UserPyHook):
	priority = {
		"pre_create": 1,
		"post_create": 1,
		"pre_modify": 1,
		"post_modify": 1,
		"pre_move": 1,
		"post_move": 1,
		"pre_remove": 1,
		"post_remove": 1
	}

	def pre_create(self, user):
		self.logger.info("Running a pre_create hook for %s.", user)

	def post_create(self, user):
		self.logger.info("Running a post_create hook for %s.", user)

	def pre_modify(self, user):
		self.logger.info("Running a pre_modify hook for %s.", user)

	def post_modify(self, user):
		self.logger.info("Running a post_modify hook for %s.", user)

	def pre_move(self, user):
		self.logger.info("Running a pre_move hook for %s.", user)

	def post_move(self, user):
		self.logger.info("Running a post_move hook for %s.", user)

	def pre_remove(self, user):
		self.logger.info("Running a pre_remove hook for %s.", user)

	def post_remove(self, user):
		self.logger.info("Running a post_remove hook for %s.", user)
