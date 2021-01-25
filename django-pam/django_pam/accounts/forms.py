#-*- coding: utf-8 -*-
#
# django_pam/accounts/forms.py
#
"""
Django PAM forms.
"""
__docformat__ = "restructuredtext en"

import logging
import inspect

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm as _AuthenticationForm

log = logging.getLogger('django_pam.accounts.forms')


class AuthenticationForm(_AuthenticationForm):
    """
    Authentication form
    """
    email = forms.EmailField(required=False, label_suffix='')

    def __init__(self, request=None, *args, **kwargs):
        if log.isEnabledFor(logging.DEBUG):
            debug = kwargs.copy()
            data = dict([(k, 'Has Password' if 'password' in k and v else v)
                         for k, v in debug.get('data', {}).items()])
            debug['data'] = data
            log.debug("request: %s, args: %s, kwargs: %s",
                      request, args, debug)

        self.base_fields['username'].label_suffix = ''
        self.base_fields['password'].label_suffix = ''
        super(AuthenticationForm, self).__init__(
            request=request, *args, **kwargs)

    def clean(self):
        """
        Does the authentication and saves the email if exists.
        """
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        email = self.cleaned_data.get('email')

        if username and password:
            self.user_cache = authenticate(
                self.request, username=username, password=password)

            if self.user_cache:
                if email:
                    self.user_cache.email = email
                    self.user_cache.save()

                self.confirm_login_allowed(self.user_cache)

        if not (username and password and self.user_cache):
            raise forms.ValidationError(
                self.error_messages['invalid_login'],
                code='invalid_login',
                params={'username': self.username_field.verbose_name},
                )

        return self.cleaned_data

    class Media:
        css = {
            'all': ('django_pam/css/auth.css',)
            }
        js = ('django_pam/js/auth.js',)
