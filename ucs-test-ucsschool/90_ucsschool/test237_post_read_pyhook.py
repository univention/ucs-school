import copy
from ucsschool.importer.utils.post_read_pyhook import PostReadPyHook


class SwitchGivenNameCnHook(PostReadPyHook):
	priority = {
		"entry_read": 1,
	}

	def entry_read(self, entry_count, input_data, input_dict):
		"""
		Run code after an entry has been read and saved in
		input_data and input_dict. This hook may alter input_data
		and input_dict to modify the input data.

		:param int entry_count: index of the data entry (e.g. line of the CSV file)
		:param list[str] input_data: input data as raw as possible (e.g. raw CSV columns). The input_data may be changed.
		:param input_dict: input data mapped to column names. The input_dict may be changed.
		:type input_dict: dict[str, str]
		:return: None
		"""
		self.logger.info('Switching firstname and lastname...')
		self.logger.debug('Before: entry_count=%r input_data=%r input_dict=%r', entry_count, input_data, input_dict)

		firstname = input_dict['Vor']
		lastname = input_dict['Nach']
		for num, entry in enumerate(copy.copy(input_data)):
			if entry == firstname:
				input_data[num] = lastname
			elif entry == lastname:
				input_data[num] = firstname
		input_dict['Vor'] = lastname
		input_dict['Nach'] = firstname

		self.logger.debug('Result: entry_count=%r input_data=%r input_dict=%r', entry_count, input_data, input_dict)
