# Generated by Django 3.1.6 on 2021-02-17 15:30

from django.db import migrations


def populate_project_consortium(apps, schema_editor):
    """
    Populates the project consortium from the default consortium and requirements.
    """
    Project = apps.get_model('jasmin_manage', 'Project')
    Requirement = apps.get_model('jasmin_manage', 'Requirement')
    Consortium = apps.get_model('jasmin_manage', 'Consortium')
    for project in Project.objects.all():
        # Start with the current default consortium
        consortium = project.default_consortium
        # If there was no default consortium set, use the consortium from the first requirement
        if not consortium:
            first_requirement = Requirement.objects.filter(service__project = project).first()
            if first_requirement:
                consortium = first_requirement.consortium
        # If the project has no requirements, just use the first consortium
        if not consortium:
            consortium = Consortium.objects.first()
        # Set the consortium and save the project
        project.consortium = consortium
        project.save()


def create_initial_collaborator(apps, schema_editor):
    """
    Moves the project owner from the project to a collaborator.
    """
    Project = apps.get_model('jasmin_manage', 'Project')
    Collaborator = apps.get_model('jasmin_manage', 'Collaborator')
    # Get the current value of the choice that corresponds to OWNER
    owner_role = next(
        value
        for value, label in Collaborator._meta.get_field('role').choices
        if label.lower() == "owner"
    )
    for project in Project.objects.all():
        # Make a new collaborator object for the owner of the project
        project.collaborators.create(user = project.owner, role = owner_role)


class Migration(migrations.Migration):

    dependencies = [
        ('jasmin_manage', '0006_auto_20210217_1529'),
    ]

    operations = [
        migrations.RunPython(populate_project_consortium),
        migrations.RunPython(create_initial_collaborator),
    ]