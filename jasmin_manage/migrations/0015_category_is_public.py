# Generated by Django 3.2.18 on 2023-03-09 12:51

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("jasmin_manage", "0014_alter_requirement_location"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="is_public",
            field=models.BooleanField(default=False),
        ),
    ]
