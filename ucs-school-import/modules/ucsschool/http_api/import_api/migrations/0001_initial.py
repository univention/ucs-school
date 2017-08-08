# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('djcelery', '__first__'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='School',
            fields=[
                ('name', models.CharField(max_length=255, serialize=False, primary_key=True)),
                ('displayName', models.CharField(max_length=255, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='TextArtifact',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('path', models.CharField(unique=True, max_length=255)),
                ('text', models.TextField(blank=True)),
            ],
            options={
                'ordering': ('-pk',),
            },
        ),
        migrations.CreateModel(
            name='UserImportJob',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('dryrun', models.BooleanField(default=True)),
                ('source_uid', models.CharField(max_length=255, blank=True)),
                ('status', models.CharField(default='New', max_length=10, choices=[('New', 'New'), ('Scheduled', 'Scheduled'), ('Started', 'Started'), ('Aborted', 'Aborted'), ('Finished', 'Finished')])),
                ('user_role', models.CharField(blank=True, max_length=20, choices=[('staff', 'staff'), ('student', 'student'), ('teacher', 'teacher'), ('teacher_and_staff', 'teacher_and_staff')])),
                ('task_id', models.CharField(max_length=40, blank=True)),
                ('basedir', models.CharField(max_length=255)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('input_file', models.FileField(upload_to='uploads/%Y-%m-%d/')),
                ('principal', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('result', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to='djcelery.TaskMeta')),
                ('school', models.ForeignKey(to='import_api.School', blank=True)),
            ],
            options={
                'ordering': ('pk',),
            },
        ),
        migrations.CreateModel(
            name='Logfile',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('import_api.textartifact',),
        ),
        migrations.CreateModel(
            name='PasswordsFile',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('import_api.textartifact',),
        ),
        migrations.CreateModel(
            name='SummaryFile',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('import_api.textartifact',),
        ),
        migrations.AddField(
            model_name='userimportjob',
            name='log_file',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to='import_api.Logfile'),
        ),
        migrations.AddField(
            model_name='userimportjob',
            name='password_file',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to='import_api.PasswordsFile'),
        ),
        migrations.AddField(
            model_name='userimportjob',
            name='summary_file',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to='import_api.SummaryFile'),
        ),
    ]
