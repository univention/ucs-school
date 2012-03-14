import time
import subprocess
import re

class AtJob(object):
	'''This class abstracts the handling of at-jobs. Use the static method
	add() in order to add a new command to the queue of at-jobs. Use the
	static methods list() and load() to get a list of all registered jobs or
	to load a specific job given an ID, respectively. The class uses time
	stamps in seconds for scheduling jobs.'''

	#TODO: it would be nice to be able to register meta information within the job file

	_regWhiteSpace = re.compile(r'\s+')
	_dateTimeFormatRead = '%a %b %d %H:%M:%S %Y'
	_dateTimeFormatWrite = '%Y-%m-%d %H:%M'
	_timeFormatWrite = '%H:%M'
	_dateFormatWrite = '%Y-%m-%d'

	# execTime: in seconds
	def __init__(self, nr, owner, execTime, isRunning):
		self.nr = nr
		self.owner = owner
		self.execTime = execTime
		self.isRunning = isRunning

	def __str__(self):
		t = time.strftime(self._dateTimeFormatWrite, time.localtime(self.execTime))
		if self.isRunning:
			t = 'running'
		return 'Job #%d (%s)' % (self.nr, t)

	def __repr__(self):
		return self.__str__()

	def rm(self):
		'''Remove the job from the queue.'''
		p = subprocess.Popen(['/usr/bin/atrm', str(self.nr)], stdout = subprocess.PIPE, stderr = subprocess.PIPE)

	# execTime: in seconds
	@staticmethod
	def add(cmd, execTime = None):
		'''Add a new command to the job queue given a time (in seconds) at which the
		job will be executed.'''

		# launch the at job directly
		atCmd = ['/usr/bin/at']
		if execTime:
			jobTime = time.strftime(AtJob._timeFormatWrite, time.localtime(execTime))
			jobDate = time.strftime(AtJob._dateFormatWrite, time.localtime(execTime))
			atCmd.extend([jobTime, jobDate])
		else:
			atCmd.append('now')
		p = subprocess.Popen(atCmd, stdout = subprocess.PIPE, stdin = subprocess.PIPE, stderr = subprocess.PIPE)

		# send the job to stdin
		p.stdin.write(cmd)
		p.stdin.close()

		# read the return value
		out = p.stdout.readline()
		p.stdout.close()

		# parse output and return job
		return AtJob._parseJob(out)

	@staticmethod
	def list():
		'''Returns a list of all registered jobs.'''
		p = subprocess.Popen('/usr/bin/atq', stdout = subprocess.PIPE, stderr = subprocess.PIPE)
		jobs = []
		for line in p.stdout:
			ijob = AtJob._parseJob(line)
			if ijob:
				jobs.append(AtJob._parseJob(line))
		return jobs

	@staticmethod
	def load(nr):
		'''Load a job given a particular ID. Returns None of job does not exist.'''
		result = [ p for p in AtJob.list() if p.nr == nr ]
		if len(result):
			return result[0]
		return None

	@staticmethod
	def _parseJob(string):
		try:
			# parse string
			tmp = AtJob._regWhiteSpace.split(string)
			execTime = time.mktime(time.strptime(' '.join(tmp[1:6]), AtJob._dateTimeFormatRead))
			isRunning = tmp[6] == '='
			owner = tmp[7]
			nr = int(tmp[0])
		except (IndexError, ValueError) as e:
			# parsing failed
			return None
		return AtJob(nr, owner, execTime, isRunning)

