from ucsschool.importer.utils.format_pyhook import FormatPyHook


SPLIT_FIRSTNAME_SPACE = 0
SPLIT_FIRSTNAME_DASH = 0
SPLIT_LASTNAME_SPACE = -1
SPLIT_LASTNAME_DASH = 0


class FormatUsernamePyHook(FormatPyHook):
	priority = {
		'patch_fields_staff': 10,
		'patch_fields_student': 10,
		'patch_fields_teacher': 10,
		'patch_fields_teacher_and_staff': 10,
	}
	properties = ('username', 'email')

	@staticmethod
	def patch_fields(fields):
		fields['firstname'] = fields['firstname'].split()[SPLIT_FIRSTNAME_SPACE].split('-')[SPLIT_FIRSTNAME_DASH]
		fields['lastname'] = fields['lastname'].split()[SPLIT_LASTNAME_SPACE].split('-')[SPLIT_LASTNAME_DASH]

	def patch_fields_staff(self, property_name, fields):
		if property_name == 'username':
			self.patch_fields(fields)
		return fields

	def patch_fields_student(self, property_name, fields):
		if property_name == 'email':
			self.patch_fields(fields)
		return fields

	def patch_fields_teacher(self, property_name, fields):
		if property_name == 'username':
			self.patch_fields(fields)
		return fields

	def patch_fields_teacher_and_staff(self, property_name, fields):
		if property_name == 'email':
			self.patch_fields(fields)
		return fields
