# Generated by Django 3.2.18 on 2023-12-20 11:15

from django.db import migrations
import jasmin_manage.models.tag


class Migration(migrations.Migration):

    dependencies = [
        ("jasmin_manage", "0022_auto_20231219_1605"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tag",
            name="name",
            field=jasmin_manage.models.tag.TagField(max_length=255, null=True),
        ),
    ]