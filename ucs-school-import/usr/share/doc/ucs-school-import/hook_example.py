from ucsschool.importer.utils.user_pyhook import UserPyHook


class MyHook(UserPyHook):
	supports_dry_run = True  # when False (default) whole class will be skipped during dry-run

	priority = {
		"pre_create": 1,  # functions with value None will be skipped
		"post_create": 1,
		"pre_modify": 1,
		"post_modify": 1,
		"pre_move": 1,
		"post_move": 1,
		"pre_remove": 1,
		"post_remove": 1
	}

	def pre_create(self, user):
		if self.dry_run:
			self.logger.info("Dry-run, skipping pre_create job for %s.", user)
		else:
			self.logger.debug("Running a pre_create hook for %s.", user)

	def post_create(self, user):
		if self.dry_run:
			self.logger.info("Dry-run, skipping post_create job for %s.", user)
		else:
			self.logger.debug("Running a post_create hook for %s.", user)

	def pre_modify(self, user):
		if self.dry_run:
			self.logger.info("Dry-run, skipping pre_modify job for %s.", user)
		else:
			self.logger.debug("Running a pre_modify hook for %s.", user)

	def post_modify(self, user):
		if self.dry_run:
			self.logger.info("Dry-run, skipping post_modify job for %s.", user)
		else:
			self.logger.debug("Running a post_modify hook for %s.", user)

	def pre_move(self, user):
		if self.dry_run:
			self.logger.info("Dry-run, skipping pre_move job for %s.", user)
		else:
			self.logger.debug("Running a pre_move hook for %s.", user)

	def post_move(self, user):
		if self.dry_run:
			self.logger.info("Dry-run, skipping post_move job for %s.", user)
		else:
			self.logger.debug("Running a post_move hook for %s.", user)

	def pre_remove(self, user):
		if self.dry_run:
			self.logger.info("Dry-run, skipping pre_remove job for %s.", user)
		else:
			self.logger.debug("Running a pre_remove hook for %s.", user)

	def post_remove(self, user):
		if self.dry_run:
			self.logger.info("Dry-run, skipping post_remove job for %s.", user)
		else:
			self.logger.debug("Running a post_remove hook for %s.", user)
