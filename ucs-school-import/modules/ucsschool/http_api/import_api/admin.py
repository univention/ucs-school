#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# SPDX-FileCopyrightText: 2017-2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""Django Admin"""

from __future__ import unicode_literals

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django_celery_results.models import TaskResult

from .models import Logfile, PasswordsFile, School, SummaryFile, UserImportJob


class UserQueryFilterMixin(object):
    ordering = ("-id",)

    def get_queryset(self, request):
        qs = super(UserQueryFilterMixin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(principal=request.user)


class ProxyModelFilterMixin(object):
    readonly_fields = ("text_loaded",)

    def get_queryset(self, request):
        qs = super(ProxyModelFilterMixin, self).get_queryset(request)
        return qs.filter(userimportjob__isnull=False)

    def text_loaded(self, instance):
        return format_html(
            "{}{}{}",
            mark_safe(  # nosec  # noqa: S308
                '<textarea class="vLargeTextField" name="text_loaded" cols="40" rows="30" readonly>'
            ),
            instance.get_text(),
            mark_safe("</textarea>"),  # nosec  # noqa: S308
        )

    text_loaded.short_description = "Text loaded from disk"
    text_loaded.allow_tags = True


@admin.register(UserImportJob)
class UserImportJobAdmin(UserQueryFilterMixin, admin.ModelAdmin):
    list_display = ("id", "school", "status", "principal", "dryrun", "user_role")
    search_fields = ("id", "school__name", "source_uid", "status", "principal__username", "user_role")
    list_filter = ("school__name", "status", "principal", "dryrun", "user_role")
    ordering = ("-id",)


@admin.register(Logfile)
class LogFileAdmin(ProxyModelFilterMixin, admin.ModelAdmin):
    pass


@admin.register(PasswordsFile)
class PasswordsFileAdmin(ProxyModelFilterMixin, admin.ModelAdmin):
    pass


@admin.register(SummaryFile)
class SummaryFileAdmin(ProxyModelFilterMixin, admin.ModelAdmin):
    pass


admin.site.unregister(TaskResult)


@admin.register(TaskResult)
class TaskMetaAdmin(UserQueryFilterMixin, admin.ModelAdmin):
    ordering = ("-id",)

    def get_queryset(self, request):
        qs = super(TaskMetaAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(userimportjob__principal=request.user)


admin.site.register(School)
