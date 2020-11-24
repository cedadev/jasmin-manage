# Generated by Django 3.0.2 on 2020-03-31 15:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('jasmin_manage', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResourceChunk',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='The name of the resource chunk, e.g. QB1, QB2.', max_length=250, unique=True)),
                ('amount', models.PositiveIntegerField(help_text='The amount of the resource that is in this chunk.')),
                ('resource', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chunks', related_query_name='chunk', to='jasmin_manage.Resource')),
            ],
            options={
                'ordering': ('resource__name', 'name'),
                'unique_together': {('resource', 'name')},
            },
        ),
    ]
