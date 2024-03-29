#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2017-2024 Univention GmbH
#
# https://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

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
