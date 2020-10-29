# Generated by Django 3.1.2 on 2020-10-23 12:37

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('jasmin_manage', '0006_auto_20201014_1057'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='project',
            name='owner',
        ),
        migrations.AlterField(
            model_name='category',
            name='resources',
            field=models.ManyToManyField(related_name='categories', related_query_name='category', to='jasmin_manage.Resource'),
        ),
        migrations.AlterField(
            model_name='requirement',
            name='number',
            field=models.PositiveIntegerField(blank=True, editable=False, help_text='The number of the requirement within the parent project.'),
        ),
        migrations.CreateModel(
            name='Collaborator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.PositiveSmallIntegerField(choices=[(20, 'Contributor'), (40, 'Owner')])),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='collaborators', related_query_name='collaborator', to='jasmin_manage.project')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('project__name', 'role', 'user__username'),
                'unique_together': {('project', 'user')},
            },
        ),
    ]