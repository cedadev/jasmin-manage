# Generated by Django 3.2 on 2021-05-27 14:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jasmin_manage', '0013_requirement_location'),
    ]

    operations = [
        migrations.AlterField(
            model_name='requirement',
            name='location',
            field=models.CharField(default='TBC', max_length=100),
        ),
    ]
