# Generated by Django 4.2.13 on 2024-05-21 14:20

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jasmin_manage", "0026_alter_tag_options_remove_tag_is_public_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="name",
            field=models.CharField(max_length=40, unique=True),
        ),
        migrations.AlterField(
            model_name="service",
            name="name",
            field=models.CharField(
                db_index=True,
                max_length=30,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Service name must start with a letter and contain lower-case letters, numbers, underscores and hyphens only.",
                        regex="^[a-z][-a-z0-9_]*\\Z",
                    )
                ],
            ),
        ),
    ]