# Generated by Django 3.2.18 on 2023-12-19 15:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jasmin_manage', '0019_remove_tag_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='tag',
            name='name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]