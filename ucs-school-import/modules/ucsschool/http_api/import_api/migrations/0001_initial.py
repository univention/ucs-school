# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('djcelery', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfigFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('version', models.IntegerField(default=0)),
                ('path', models.CharField(max_length=255, blank=True)),
                ('enabled', models.BooleanField(default=True)),
                ('user_role', models.CharField(max_length=20, choices=[('staff', 'Staff'), ('student', 'Student'), ('teacher', 'Teacher'), ('teacher_and_staff', 'Teacher and Staff')])),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ('school', 'user_role', '-version', '-pk'),
            },
        ),
        migrations.CreateModel(
            name='Hook',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('version', models.IntegerField(default=0)),
                ('type', models.CharField(default='PyHook', max_length=10, choices=[('LegacyHook', 'LegacyHook'), ('PyHook', 'PyHook')])),
                ('object', models.CharField(default='user', max_length=32, choices=[('group', 'group'), ('ou', 'ou'), ('user', 'user')])),
                ('action', models.CharField(default='create', max_length=32, choices=[('create', 'create'), ('modify', 'modify'), ('move', 'move'), ('remove', 'remove')])),
                ('time', models.CharField(default='pre', max_length=32, choices=[('pre', 'pre'), ('post', 'post')])),
                ('approved', models.BooleanField(default=False)),
                ('mandatory', models.BooleanField(default=False)),
                ('enabled', models.BooleanField(default=True)),
                ('text', models.TextField(blank=True)),
                ('path', models.CharField(max_length=255, blank=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ('school', 'name', '-version', '-pk'),
            },
        ),
        migrations.CreateModel(
            name='Logfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('path', models.CharField(unique=True, max_length=255)),
                ('text', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='School',
            fields=[
                ('name', models.CharField(max_length=255, serialize=False, primary_key=True)),
                ('displayName', models.CharField(max_length=255, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserImportJob',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('source_uid', models.CharField(max_length=255)),
                ('status', models.CharField(default='New', max_length=10, choices=[('New', 'New'), ('Scheduled', 'Scheduled'), ('Started', 'Started'), ('Aborted', 'Aborted'), ('Finished', 'Finished')])),
                ('task_id', models.CharField(max_length=40, blank=True)),
                ('principal', models.CharField(max_length=255)),
                ('progress', models.TextField(blank=True)),
                ('dryrun', models.BooleanField(default=True)),
                ('basedir', models.CharField(max_length=255)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('input_file', models.FileField(upload_to='uploads/%Y-%m-%d/')),
                ('input_file_type', models.CharField(default='csv', max_length=10, choices=[('csv', 'csv')])),
                ('config_file', models.ForeignKey(to='import_api.ConfigFile')),
                ('hooks', models.ManyToManyField(to='import_api.Hook', blank=True)),
                ('log_file', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to='import_api.Logfile')),
                ('result', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, blank=True, to='djcelery.TaskMeta')),
                ('school', models.ForeignKey(to='import_api.School')),
            ],
            options={
                'ordering': ('-pk',),
            },
        ),
        migrations.AddField(
            model_name='hook',
            name='school',
            field=models.ForeignKey(to='import_api.School'),
        ),
        migrations.AddField(
            model_name='configfile',
            name='school',
            field=models.ForeignKey(to='import_api.School'),
        ),
        migrations.AlterUniqueTogether(
            name='hook',
            unique_together=set([('school', 'version', 'name')]),
        ),
        migrations.AlterUniqueTogether(
            name='configfile',
            unique_together=set([('school', 'version', 'user_role')]),
        ),
    ]
