# Generated by Django 3.2.18 on 2023-12-20 11:17

from django.db import migrations
import jasmin_manage.models.tag


class Migration(migrations.Migration):

    dependencies = [
        ("jasmin_manage", "0023_alter_tag_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="tag",
            name="name",
            field=jasmin_manage.models.tag.TagField(
                max_length=255, null=True, unique=True
            ),
        ),
    ]