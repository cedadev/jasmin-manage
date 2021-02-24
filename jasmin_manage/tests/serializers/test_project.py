import random
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, force_authenticate

from ...models import (
    Category,
    Collaborator,
    Consortium,
    Project,
    Requirement,
    Resource,
    Service
)
from ...serializers import ProjectSerializer


class ProjectSerializerTestCase(TestCase):
    """
    Tests for the project serializer.
    """
    @classmethod
    def setUpTestData(cls):
        # Set up a consortium and project to use
        cls.consortium = Consortium.objects.create(
            name = 'Consortium 1',
            description = 'some description',
            manager = get_user_model().objects.create_user('manager1')
        )
        cls.owner = get_user_model().objects.create_user('owner1')

    def setUp(self):
        # Make the project in setUp so that we can safely modify it
        self.project = self.consortium.projects.create(
            name = 'Project 1',
            description = 'some description',
            owner = self.owner
        )

    def test_renders_instance_correctly(self):
        """
        Tests that the serializer renders an existing instance correctly.
        """
        # Add some services and requirements to the project
        category = Category.objects.create(name = 'Category 1', description = 'Some description')
        resource = Resource.objects.create(name = 'Resource 1', description = 'Some description')
        services = []
        for i in range(5):
            services.append(self.project.services.create(name = f'service{i}', category = category))
        for i in range(20):
            random.choice(services).requirements.create(resource = resource, amount = 100)
        # In order to render the links correctly, there must be a request in the context
        request = APIRequestFactory().post('/projects/{}/'.format(self.project.pk))
        # In order for the current_user_role to get populated, we need to authenticate the request
        force_authenticate(request, self.owner)
        serializer = ProjectSerializer(self.project, context = dict(request = Request(request)))
        # Check that the right keys are present
        self.assertCountEqual(
            serializer.data.keys(),
            {
                'id',
                'name',
                'description',
                'status',
                'consortium',
                'num_services',
                'num_requirements',
                'num_collaborators',
                'current_user_role',
                'created_at',
                '_links'
            }
        )
        # Check the the values are correct
        # Don't explicitly check the links field - it has tests
        self.assertEqual(serializer.data['id'], self.project.pk)
        self.assertEqual(serializer.data['name'], self.project.name)
        self.assertEqual(serializer.data['description'], self.project.description)
        self.assertEqual(serializer.data['status'], Project.Status.EDITABLE.name)
        self.assertEqual(serializer.data['consortium'], self.consortium.pk)
        self.assertEqual(serializer.data['num_services'], 5)
        self.assertEqual(serializer.data['num_requirements'], 20)
        self.assertEqual(serializer.data['num_collaborators'], 1)
        self.assertEqual(serializer.data['current_user_role'], Collaborator.Role.OWNER.name)

    def test_create_uses_authenticated_user_as_owner(self):
        """
        Tests that the serializer uses the authenticated user as the project owner.
        """
        user = get_user_model().objects.create_user('user1')
        # This is the interface we require from request
        request = SimpleNamespace(user = user)
        serializer = ProjectSerializer(
            data = dict(
                consortium = self.consortium.pk,
                name = 'Project 2',
                description = 'some description'
            ),
            context = dict(request = request)
        )
        self.assertTrue(serializer.is_valid())
        project = serializer.save()
        project.refresh_from_db()
        self.assertEqual(project.consortium.pk, self.consortium.pk)
        self.assertEqual(project.name, 'Project 2')
        self.assertEqual(project.status, Project.Status.EDITABLE)
        self.assertEqual(len(project.collaborators.all()), 1)
        self.assertEqual(project.collaborators.first().user.pk, user.pk)

    def test_create_enforces_required_fields_present(self):
        """
        Tests that the required fields are enforced on create.
        """
        serializer = ProjectSerializer(data = {})
        self.assertFalse(serializer.is_valid())
        required_fields = {'consortium', 'name', 'description'}
        self.assertCountEqual(serializer.errors.keys(), required_fields)
        for name in required_fields:
            self.assertEqual(serializer.errors[name][0].code, 'required')

    def test_create_enforces_required_fields_not_blank(self):
        """
        Tests that the required fields cannot be blank on create.
        """
        serializer = ProjectSerializer(
            data = dict(
                consortium = self.consortium.pk,
                name = '',
                description = ''
            )
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {'name', 'description'})
        for name in {'name', 'description'}:
            self.assertEqual(serializer.errors[name][0].code, 'blank')

    def test_create_enforces_unique_name(self):
        """
        Tests that the uniqueness constraint is enforced on name.
        """
        # Try to create another project with the same name as the existing project
        serializer = ProjectSerializer(
            data = dict(
                consortium = self.consortium.pk,
                name = 'Project 1',
                description = 'some description'
            )
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {'name'})
        self.assertEqual(serializer.errors['name'][0].code, 'unique')

    def test_cannot_create_with_invalid_consortium(self):
        """
        Tests that attempting to create with an invalid consortium will fail.
        """
        serializer = ProjectSerializer(
            data = dict(
                consortium = 10,
                name = 'Project 2',
                description = 'some description'
            )
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {'consortium'})
        self.assertEqual(serializer.errors['consortium'][0].code, 'does_not_exist')

    def test_cannot_specify_status_on_create(self):
        """
        Tests that the status cannot be specified on create.
        """
        user = get_user_model().objects.create_user('user1')
        serializer = ProjectSerializer(
            data = dict(
                consortium = self.consortium.pk,
                name = 'Project 2',
                description = 'some description',
                status = Project.Status.UNDER_REVIEW.name
            ),
            # This is the interface we require from request
            context = dict(request = SimpleNamespace(user = user))
        )
        self.assertTrue(serializer.is_valid())
        project = serializer.save()
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.EDITABLE)

    def test_update_name_and_description(self):
        """
        Tests that the name and description can be updated.
        """
        serializer = ProjectSerializer(
            self.project,
            data = dict(name = 'New project name', description = 'new description')
        )
        self.assertTrue(serializer.is_valid())
        project = serializer.save()
        project.refresh_from_db()
        self.assertEqual(project.name, 'New project name')
        self.assertEqual(project.description, 'new description')

    def test_update_enforces_required_fields_not_blank(self):
        """
        Tests that the required fields cannot be blank on update.
        """
        serializer = ProjectSerializer(self.project, data = dict(name = '', description = ''))
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {'name', 'description'})
        for name in {'name', 'description'}:
            self.assertEqual(serializer.errors[name][0].code, 'blank')

    def test_update_enforces_unique_name(self):
        """
        Tests that the unique constraint is enforced for name on update.
        """
        # Make a project with a name that we will collide with on update
        self.consortium.projects.create(
            name = 'New project name',
            description = 'some description',
            owner = self.owner
        )
        serializer = ProjectSerializer(
            self.project,
            data = dict(name = 'New project name'),
            partial = True
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {'name'})
        self.assertEqual(serializer.errors['name'][0].code, 'unique')

    def test_cannot_update_consortium(self):
        """
        Tests that the consortium cannot be updated.
        """
        self.assertEqual(self.project.consortium.pk, self.consortium.pk)
        # Make another valid consortium to update to
        consortium = Consortium.objects.create(
            name = 'Consortium 2',
            description = 'some description',
            manager = get_user_model().objects.create_user('manager2')
        )
        serializer = ProjectSerializer(
            self.project,
            data = dict(consortium = consortium.pk),
            partial = True
        )
        # The validation should pass, but the consortium will not change
        self.assertTrue(serializer.is_valid())
        project = serializer.save()
        project.refresh_from_db()
        self.assertEqual(project.consortium.pk, self.consortium.pk)

    def test_cannot_update_status(self):
        """
        Tests that the status cannot be updated.
        """
        self.assertEqual(self.project.status, Project.Status.EDITABLE)
        serializer = ProjectSerializer(
            self.project,
            data = dict(status = Project.Status.UNDER_REVIEW.name),
            partial = True
        )
        # The validation should pass, but the consortium will not change
        self.assertTrue(serializer.is_valid())
        project = serializer.save()
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.EDITABLE)
