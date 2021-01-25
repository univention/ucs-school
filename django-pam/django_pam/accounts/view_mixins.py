# -*- coding: utf-8 -*-
#
# django_pam/accounts/view_mixins.py
#

"""
Dynamic Column view mixins.
"""
__docformat__ = "restructuredtext en"

import logging

from django.http import JsonResponse

log = logging.getLogger('django_pam.accounts.views')


class JSONResponseMixin(object):
    """
    A mixin that can be used to render a JSON response.
    """

    def render_to_json_response(self, context, **response_kwargs):
        """
        Returns a JSON response, transforming 'context' to make the payload.

        :param context: The template rendering context.
        :type context: See `Django Context <https://docs.djangoproject.com/en/dev/ref/templates/api/#playing-with-context-objects>`_.
        :param response_kwargs: Response keywords arguments.
        :rtype: See `Django response_class <https://docs.djangoproject.com/en/dev/ref/class-based-views/mixins-simple/#django.views.generic.base.TemplateResponseMixin.response_class>`_.
        """
        return JsonResponse(self.get_data(**context), **response_kwargs)

    def get_data(self, **context):
        """
        Returns an object that will be serialized as JSON by json.dumps().

        :param context: Context added to the JSON response.
        :type context: dict
        :rtype: dict -- Updated context
        """
        # Note: This is *EXTREMELY* naive; in reality, you'll need
        # to do much more complex handling to ensure that arbitrary
        # objects -- such as Django model instances or querysets
        # -- can be serialized as JSON.
        return context

class AjaxableResponseMixin(object):
    """
    Mixin to add AJAX support to a form. Must be used with an object-based
    FormView (e.g. CreateView)
    """

    def form_invalid(self, form):
        """
        Renders the invalid form error description. See `Django's form_invalid
        <https://docs.djangoproject.com/en/dev/ref/class-based-views/mixins-editing/#django.views.generic.edit.FormMixin.form_invalid>`_.
        If the request is an AJAX request return this data as a JSON string.

        :param form: The Django form object.
        :type form: Django's form object.
        :rtype: Result from Django's ``form_valid`` or a JSON string.
        """
        response = super(AjaxableResponseMixin, self).form_invalid(form)

        if self.request.is_ajax():
            return JsonResponse(form.errors, status=422)
        else:
            return response

    def form_valid(self, form):
        """
        Renders the valid data. See `Django's form_valid <https://docs.djangoproject.com/en/dev/ref/class-based-views/mixins-editing/#django.views.generic.edit.FormMixin.form_valid>`_.
        If the request is an AJAX request return this data as a JSON string.

        :param form: The Django form object.
        :type form: Django's form object.
        :rtype: Result from Django's ``form_valid`` or a JSON string.
        """
        # We make sure to call the parent's form_valid() method because
        # it might do some processing (in the case of CreateView, it will
        # call form.save() for example).
        response = super(AjaxableResponseMixin, self).form_valid(form)

        if self.request.is_ajax():
            return JsonResponse(self.get_data(**{}))
        else:
            return response

    def get_data(self, **context):
        """
        Returns an object that will be serialized as JSON by json.dumps().

        :param context: Context added to the JSON response.
        :type context: dict
        :rtype: dict -- Updated context
        """
        context.update({'pk': self.object.pk})
        return context
