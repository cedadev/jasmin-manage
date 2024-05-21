# Generated by Django 4.2.13 on 2024-05-17 10:18

import django.core.validators
from django.db import migrations, models
import jasmin_manage.models.tag


class Migration(migrations.Migration):

    dependencies = [
        ("jasmin_manage", "0025_tag_is_public"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="tag",
            options={"ordering": ("name",)},
        ),
        migrations.RemoveField(
            model_name="tag",
            name="is_public",
        ),
        migrations.AlterField(
            model_name="project",
            name="name",
            field=models.CharField(max_length=30, unique=True),
        ),
        migrations.AlterField(
            model_name="project",
            name="tags",
            field=models.ManyToManyField(
                blank=True,
                related_name="project",
                related_query_name="project",
                to="jasmin_manage.tag",
            ),
        ),
        migrations.AlterField(
            model_name="service",
            name="name",
            field=models.CharField(
                db_index=True,
                max_length=20,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Service name must start with a letter and contain lower-case letters, numbers, underscores and hyphens only.",
                        regex="^[a-z][-a-z0-9_]*\\Z",
                    )
                ],
            ),
        ),
        migrations.AlterField(
            model_name="tag",
            name="name",
            field=jasmin_manage.models.tag.TagField(
                max_length=15, null=True, unique=True
            ),
        ),
    ]