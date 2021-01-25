# -*- coding: utf-8 -*-
#
# django_pam/urls.py
#

"""
Django PAM urls.py
"""
__docformat__ = "restructuredtext en"

try:
    from django.urls import include, re_path
except:
    from django.conf.urls import include, url as re_path


app_name = 'django-pam'
urlpatterns = [
    re_path(r'^', include('django_pam.accounts.urls')),
    ]
