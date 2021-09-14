#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Univention UCS@school
#
# Copyright 2017-2021 Univention GmbH
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

from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    replaces = [
        ("import_api", "0001_initial"),
        ("import_api", "0002_auto_20180309_1104"),
        ("import_api", "0003_auto_20180601_0848"),
    ]

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("django_celery_results", "__first__"),
    ]

    operations = [
        migrations.CreateModel(
            name="School",
            fields=[
                ("name", models.CharField(max_length=255, primary_key=True, serialize=False)),
                ("displayName", models.CharField(blank=True, max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name="TextArtifact",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("path", models.CharField(max_length=255, unique=True)),
                ("text", models.TextField(blank=True)),
            ],
            options={
                "ordering": ("-pk",),
            },
        ),
        migrations.CreateModel(
            name="UserImportJob",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("dryrun", models.BooleanField(default=True)),
                ("source_uid", models.CharField(blank=True, max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("New", "New"),
                            ("Scheduled", "Scheduled"),
                            ("Started", "Started"),
                            ("Aborted", "Aborted"),
                            ("Finished", "Finished"),
                        ],
                        default="New",
                        max_length=10,
                    ),
                ),
                (
                    "user_role",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("staff", "staff"),
                            ("student", "student"),
                            ("teacher", "teacher"),
                            ("teacher_and_staff", "teacher_and_staff"),
                        ],
                        max_length=20,
                    ),
                ),
                ("task_id", models.CharField(blank=True, max_length=40)),
                ("basedir", models.CharField(max_length=255)),
                ("date_created", models.DateTimeField(auto_now_add=True)),
                ("input_file", models.FileField(upload_to="uploads/%Y-%m-%d/")),
                (
                    "principal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
                    ),
                ),
                (
                    "result",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="django_celery_results.TaskResult",
                    ),
                ),
                (
                    "school",
                    models.ForeignKey(
                        blank=True, on_delete=django.db.models.deletion.CASCADE, to="import_api.School"
                    ),
                ),
            ],
            options={
                "ordering": ("pk",),
            },
        ),
        migrations.CreateModel(
            name="Logfile",
            fields=[],
            options={
                "proxy": True,
            },
            bases=("import_api.textartifact",),
        ),
        migrations.CreateModel(
            name="PasswordsFile",
            fields=[],
            options={
                "proxy": True,
            },
            bases=("import_api.textartifact",),
        ),
        migrations.CreateModel(
            name="SummaryFile",
            fields=[],
            options={
                "proxy": True,
            },
            bases=("import_api.textartifact",),
        ),
        migrations.AddField(
            model_name="userimportjob",
            name="log_file",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="userimportjob_log_file",
                to="import_api.Logfile",
            ),
        ),
        migrations.AddField(
            model_name="userimportjob",
            name="password_file",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="userimportjob_password_file",
                to="import_api.PasswordsFile",
            ),
        ),
        migrations.AddField(
            model_name="userimportjob",
            name="summary_file",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="userimportjob_summary_file",
                to="import_api.SummaryFile",
            ),
        ),
        migrations.CreateModel(
            name="Role",
            fields=[
                ("name", models.CharField(max_length=255, primary_key=True, serialize=False)),
                ("displayName", models.CharField(blank=True, max_length=255)),
            ],
            options={
                "ordering": ("name",),
            },
        ),
        migrations.AlterModelOptions(
            name="school",
            options={"ordering": ("name",)},
        ),
    ]
