# Generated by Django 3.1.2 on 2020-10-29 22:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jasmin_manage', '0009_auto_20201023_1346'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='project',
            name='next_requirement_number',
        ),
        migrations.RemoveField(
            model_name='requirement',
            name='number',
        ),
        migrations.AlterField(
            model_name='collaborator',
            name='role',
            field=models.PositiveSmallIntegerField(choices=[(20, 'Contributor'), (40, 'Owner')], default=20),
        ),
    ]
