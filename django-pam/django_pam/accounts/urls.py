# -*- coding: utf-8 -*-
#
# django_pam/accounts/urls.py
#

"""
Django PAM accounta/urls.py

"""
__docformat__ = "restructuredtext en"

try:
    from django.urls import include, re_path
except:
    from django.conf.urls import include, url as re_path


from django.views.generic import TemplateView

from .views import LoginView, LogoutView


urlpatterns = [
    re_path(r'^login/$', LoginView.as_view(), name='login'),
    re_path(r'^logout/$', LogoutView.as_view(), name='logout'),
    ]
