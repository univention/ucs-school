==========
Django PAM
==========

.. image:: http://img.shields.io/pypi/v/django-pam.svg
   :target: https://pypi.python.org/pypi/django-pam
   :alt: PyPI Version

.. image:: http://img.shields.io/pypi/wheel/django-pam.svg
   :target: https://pypi.python.org/pypi/django-pam
   :alt: PyPI Wheel

.. image:: http://img.shields.io/pypi/pyversions/django-pam.svg
   :target: https://pypi.python.org/pypi/django-pam
   :alt: Python Versions

.. image:: http://img.shields.io/pypi/l/django-pam.svg
   :target: https://pypi.python.org/pypi/django-pam
   :alt: License

A Django PAM authentication backend implementation.

The MIT License (MIT)

Overview
--------

This is a simple authentication backend that uses the
`python-pam <https://github.com/FirefighterBlu3/python-pam>`_
package. Django PAM can be used in an SSO (Single Sign On) environment
or just with a single box where you want to log into a Django app with
your UNIX login.

Updated for Django 3.x.

Provides
--------

1. PAM Authentication Backend

2. Login and Logout Views

3. Templates for both standard and modal authentication.

4. Supporting JavaScript and CSS.

Quick Start
-----------

You will need to add Django PAM to your ``INSTALLED_APPS``::

  INSTALLED_APPS = [
      ...
      'django_pam',
  ]

Next you will need to add the Django PAM backend to the ``AUTHENTICATION_BACKENDS``::

  AUTHENTICATION_BACKENDS = [
      'django_pam.auth.backends.PAMBackend',
      'django.contrib.auth.backends.ModelBackend',
  ]

The user that runs the application needs to be a member of the
``/etc/shadow`` file group, this is usually the web server user. This
is necessary so the web server can authenticate other users. To do
this run the command below with the proper user::

  $ sudo usermod -a -G shadow <user>

Complete Documentation can be found on
`Read the Docs <https://readthedocs.org/>`_ at:
`Django PAM <http://django-pam.readthedocs.io/en/latest/>`_
