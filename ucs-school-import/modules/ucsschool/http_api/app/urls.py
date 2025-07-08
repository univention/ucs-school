# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# SPDX-FileCopyrightText: 2017-2025 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""URLs"""

from __future__ import unicode_literals

from django.conf.urls import include, url
from django.contrib import admin
from rest_framework import routers

# from rest_framework.documentation import include_docs_urls  # DRF >= 3.6.0
from ..import_api import views

router = routers.DefaultRouter()
router.register(r"roles", views.RoleViewSet)
router.register(r"schools", views.SchoolViewSet)
router.register(r"imports/users", views.UserImportJobViewSet)

urlpatterns = [
    # url(r'^docs/', include_docs_urls(title='UCS@school import API'))
    url(r"^admin/", admin.site.urls),
    url(r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    # URLs for hyperlinked relationships from imports/users/<ID>/<log|pass|sum>/ back to
    # imports/users/<ID>/
    url(
        r"^(?P<version>(v1))/imports/users/(?P<pk>\d+)/logfile/",
        views.LogFileViewSet.as_view({"get": "retrieve"}),
        name="logfile-detail",
    ),
    url(
        r"^(?P<version>(v1))/imports/users/(?P<pk>\d+)/passwords/",
        views.PasswordsViewSet.as_view({"get": "retrieve"}),
        name="passwordsfile-detail",
    ),
    url(
        r"^(?P<version>(v1))/imports/users/(?P<pk>\d+)/summary/",
        views.SummaryViewSet.as_view({"get": "retrieve"}),
        name="summaryfile-detail",
    ),
    url(r"^(?P<version>(v1))/", include(router.urls)),
]
