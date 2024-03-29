# Generated by Django 3.1.6 on 2021-02-17 15:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("jasmin_manage", "0007_auto_20210217_1530"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="project",
            name="default_consortium",
        ),
        migrations.RemoveField(
            model_name="project",
            name="owner",
        ),
        migrations.RemoveField(
            model_name="requirement",
            name="consortium",
        ),
        migrations.AlterField(
            model_name="project",
            name="consortium",
            field=models.ForeignKey(
                default=0,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="projects",
                related_query_name="project",
                to="jasmin_manage.consortium",
            ),
            preserve_default=False,
        ),
    ]
