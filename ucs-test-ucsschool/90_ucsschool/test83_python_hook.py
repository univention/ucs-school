# -*- coding: utf-8 -*-

from ucsschool.lib.models.hook import Hook
IMPORT_VAR

print('*********** HOOK **********')
print('*********** __file__={!r}'.format(__file__))

TARGET_FILE = 'TARGET_FILE_VAR'
print('*********** TARGET_FILE={!r}'.format(TARGET_FILE))

class Test83Hook(Hook):
	model = MODEL_CLASS_VAR
	priority = {
		"pre_create": 1,
		"post_create": 1,
		"pre_modify": 1,
		"post_modify": 1,
		"pre_move": 1,
		"post_move": 1,
		"pre_remove": 1,
		"post_remove": 1,
	}
	print('*********** model={!r}'.format(model))

	def __init__(self, lo, *args, **kwargs):
		print('*********** __init__() self.model={!r}'.format(self.model))
		super(Test83Hook, self).__init__(lo, *args, **kwargs)
		self.logger.info('model: %r', self.model.__name__)

	def _log(self, *args):
		self.logger.debug('Writing "%s" to %r...', ' '.join(str(a) for a in args), TARGET_FILE)
		with open(TARGET_FILE, 'a') as fp:
			fp.write('{}\n'.format(' '.join(str(a) for a in args)))

	def pre_create(self, obj):
		print('*********** pre_create() self.model={!r} obj={!r} obj.school={!r}'.format(self.model, obj, obj.school))
		self._log('pre_create', self.model.__name__, obj.name, obj.school)

	def post_create(self, obj):
		print('*********** post_create() self.model={!r} obj={!r} obj.school={!r}'.format(self.model, obj, obj.school))
		self._log('post_create', self.model.__name__, obj.name, obj.school)

	def pre_modify(self, obj):
		self._log('pre_modify', self.model.__name__, obj.name, obj.school)

	def post_modify(self, obj):
		self._log('post_modify', self.model.__name__, obj.name, obj.school)

	def pre_move(self, obj):
		self._log('pre_move', self.model.__name__, obj.name, obj.school)

	def post_move(self, obj):
		self._log('post_move', self.model.__name__, obj.name, obj.school)

	def pre_remove(self, obj):
		self._log('pre_remove', self.model.__name__, obj.name, obj.school)

	def post_remove(self, obj):
		self._log('post_remove', self.model.__name__, obj.name, obj.school)
