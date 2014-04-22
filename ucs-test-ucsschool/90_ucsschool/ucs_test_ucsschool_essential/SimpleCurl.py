#!/usr/share/ucs-test/runner python

import pycurl
import StringIO
import os


"""""""""""""""""""""""""""""""""""""""
  Class SimpleCurl
"""""""""""""""""""""""""""""""""""""""

class SimpleCurl(object):

	def __init__(
			self,
			proxy,
			username='Administrator',
			password='univention',
			bFollowLocation=1,
			maxReDirs=5,
			connectTimout=10,
			timeOut=10,
			port=3128,
			auth=pycurl.HTTPAUTH_BASIC):
			# Perform basic authentication by default
		self.curl = pycurl.Curl()
		self.curl.setopt(pycurl.FOLLOWLOCATION, bFollowLocation)
		self.curl.setopt(pycurl.MAXREDIRS, maxReDirs)
		self.curl.setopt(pycurl.CONNECTTIMEOUT, connectTimout)
		self.curl.setopt(pycurl.TIMEOUT, timeOut)
		self.curl.setopt(pycurl.PROXY, proxy)
		self.curl.setopt(pycurl.PROXYPORT, port)
		self.cookieFilename = os.tempnam()
		self.curl.setopt(pycurl.COOKIEFILE, self.cookieFilename)
		self.curl.setopt(pycurl.COOKIEJAR, self.cookieFilename)
		self.curl.setopt(pycurl.PROXYUSERPWD, "%s:%s" % (username, password))
		self.curl.setopt(pycurl.PROXYAUTH, auth)

	def getPage(self, url, bVerbose, postData=None):
		self.curl.setopt(pycurl.URL, str(url))
		self.curl.setopt(pycurl.VERBOSE, bVerbose)
		if postData:
			self.curl.setopt(pycurl.HTTPPOST, postData)
		buf = StringIO.StringIO()
		self.curl.setopt(pycurl.WRITEFUNCTION, buf.write)
		self.curl.perform()
		page = buf.getvalue()
		buf.close()
		return page

	def httpCode(self):
		return self.curl.getinfo(pycurl.HTTP_CODE)

	def __del__(self):
		self.curl.close()
		if os.path.exists(self.cookieFilename):
			os.remove(self.cookieFilename)

