import random

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
    Service,
)
from ...serializers import ProjectSerializer


class ProjectSerializerTestCase(TestCase):
    """
    Tests for the project serializer.
    """

    @classmethod
    def setUpTestData(cls):
        # Set up a public consortium and a non-public consortium to use
        cls.public_consortium = Consortium.objects.create(
            name="Public Consortium",
            description="some description",
            is_public=True,
            manager=get_user_model().objects.create_user("manager1"),
        )
        cls.non_public_consortium = Consortium.objects.create(
            name="Private Consortium",
            description="Some description.",
            is_public=False,
            manager=get_user_model().objects.create_user("manager2"),
        )
        cls.owner = get_user_model().objects.create_user("owner1")

    def make_project_create_request(self, user):
        """
        Makes a fake request for the project.
        """
        request = APIRequestFactory().post("/projects/")
        force_authenticate(request, user)
        return Request(request)

    def test_renders_instance_correctly(self):
        """
        Tests that the serializer renders an existing instance correctly.
        """
        project = self.public_consortium.projects.create(
            name="Project 1", description="some description", owner=self.owner
        )
        # Add some services and requirements to the project
        category = Category.objects.create(
            name="Category 1", description="Some description"
        )
        resource = Resource.objects.create(
            name="Resource 1", description="Some description"
        )
        services = []
        for i in range(5):
            services.append(
                project.services.create(name=f"service{i}", category=category)
            )
        for i in range(20):
            random.choice(services).requirements.create(resource=resource, amount=100)
        # In order to render the links correctly, there must be a request in the context
        request = APIRequestFactory().post("/projects/{}/".format(project.pk))
        # In order for the current_user_role to get populated, we need to authenticate the request
        force_authenticate(request, self.owner)
        serializer = ProjectSerializer(project, context=dict(request=Request(request)))
        # Check that the right keys are present
        self.assertCountEqual(
            serializer.data.keys(),
            {
                "id",
                "name",
                "description",
                "status",
                "consortium",
                "num_services",
                "num_requirements",
                "num_collaborators",
                "current_user_role",
                "created_at",
                "tags",
                "fairshare",
                "_links",
            },
        )
        # Check the the values are correct
        # Don't explicitly check the links field - it has tests
        self.assertEqual(serializer.data["id"], project.pk)
        self.assertEqual(serializer.data["name"], project.name)
        self.assertEqual(serializer.data["description"], project.description)
        self.assertEqual(serializer.data["status"], Project.Status.EDITABLE.name)
        self.assertEqual(serializer.data["consortium"], self.public_consortium.pk)
        self.assertEqual(serializer.data["num_services"], 5)
        self.assertEqual(serializer.data["num_requirements"], 20)
        self.assertEqual(serializer.data["num_collaborators"], 1)
        self.assertEqual(
            serializer.data["current_user_role"], Collaborator.Role.OWNER.name
        )

    def test_create_uses_authenticated_user_as_owner(self):
        """
        Tests that the serializer uses the authenticated user as the project owner.
        """
        user = get_user_model().objects.create_user("user1")
        # Get a request that is authenticated as the given user
        request = self.make_project_create_request(user)
        serializer = ProjectSerializer(
            data=dict(
                consortium=self.public_consortium.pk,
                name="Project 2",
                description="some description",
            ),
            context=dict(request=request),
        )
        self.assertTrue(serializer.is_valid())
        project = serializer.save()
        project.refresh_from_db()
        self.assertEqual(project.consortium.pk, self.public_consortium.pk)
        self.assertEqual(project.name, "Project 2")
        self.assertEqual(project.status, Project.Status.EDITABLE)
        self.assertEqual(len(project.collaborators.all()), 1)
        self.assertEqual(project.collaborators.first().user.pk, user.pk)

    def test_create_with_non_public_consortium_and_staff_user(self):
        """
        Tests that the serializer permits a staff user to create a project with a
        non-public consortium.
        """
        # Make a staff user and authenticate them with a request
        staff_user = get_user_model().objects.create_user("staff_user", is_staff=True)
        request = self.make_project_create_request(staff_user)
        serializer = ProjectSerializer(
            data=dict(
                consortium=self.non_public_consortium.pk,
                name="Project 2",
                description="some description",
            ),
            context=dict(request=request),
        )
        self.assertTrue(serializer.is_valid())
        project = serializer.save()
        project.refresh_from_db()
        self.assertEqual(project.consortium.pk, self.non_public_consortium.pk)
        self.assertEqual(project.name, "Project 2")
        self.assertEqual(project.status, Project.Status.EDITABLE)
        self.assertEqual(len(project.collaborators.all()), 1)
        self.assertEqual(project.collaborators.first().user.pk, staff_user.pk)

    def test_create_enforces_required_fields_present(self):
        """
        Tests that the required fields are enforced on create.
        """
        user = get_user_model().objects.create_user("user1")
        request = self.make_project_create_request(user)
        serializer = ProjectSerializer(data={}, context=dict(request=request))
        self.assertFalse(serializer.is_valid())
        required_fields = {"consortium", "name", "description"}
        self.assertCountEqual(serializer.errors.keys(), required_fields)
        for name in required_fields:
            self.assertEqual(serializer.errors[name][0].code, "required")

    def test_create_enforces_required_fields_not_blank(self):
        """
        Tests that the required fields cannot be blank on create.
        """
        user = get_user_model().objects.create_user("user1")
        request = self.make_project_create_request(user)
        serializer = ProjectSerializer(
            data=dict(consortium=self.public_consortium.pk, name="", description=""),
            context=dict(request=request),
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {"name", "description"})
        for name in {"name", "description"}:
            self.assertEqual(serializer.errors[name][0].code, "blank")

    def test_create_enforces_unique_name(self):
        """
        Tests that the uniqueness constraint is enforced on name.
        """
        project = self.public_consortium.projects.create(
            name="Project 1", description="some description", owner=self.owner
        )
        # Try to create another project with the same name as the existing project
        user = get_user_model().objects.create_user("user1")
        request = self.make_project_create_request(user)
        serializer = ProjectSerializer(
            data=dict(
                consortium=self.public_consortium.pk,
                name="Project 1",
                description="some description",
            ),
            context=dict(request=request),
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {"name"})
        self.assertEqual(serializer.errors["name"][0].code, "unique")

    def test_cannot_create_with_invalid_consortium(self):
        """
        Tests that attempting to create with an invalid consortium will fail.
        """
        user = get_user_model().objects.create_user("user1")
        request = self.make_project_create_request(user)
        serializer = ProjectSerializer(
            data=dict(consortium=10, name="Project 2", description="some description"),
            context=dict(request=request),
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {"consortium"})
        self.assertEqual(serializer.errors["consortium"][0].code, "does_not_exist")

    def test_cannot_create_with_non_staff_and_non_public_consortium(self):
        """
        Tests that attempting to create a project in a non-public consortium as a
        non-staff user fails.
        """
        # Make a regular user and authenticate them with a request
        user = get_user_model().objects.create_user("user1")
        request = self.make_project_create_request(user)
        # Try to use the serializer to make a project in a non-public consortium
        serializer = ProjectSerializer(
            data=dict(
                consortium=self.non_public_consortium.pk,
                name="Project 2",
                description="some description",
            ),
            context=dict(request=request),
        )
        # It should fail with a suitable error on the consortium field
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {"consortium"})
        self.assertEqual(
            serializer.errors["consortium"][0].code, "non_public_consortium"
        )

    def test_cannot_specify_status_on_create(self):
        """
        Tests that the status cannot be specified on create.
        """
        user = get_user_model().objects.create_user("user1")
        request = self.make_project_create_request(user)
        serializer = ProjectSerializer(
            data=dict(
                consortium=self.public_consortium.pk,
                name="Project 2",
                description="some description",
                status=Project.Status.UNDER_REVIEW.name,
            ),
            context=dict(request=request),
        )
        self.assertTrue(serializer.is_valid())
        project = serializer.save()
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.EDITABLE)

    def test_update_name_and_description(self):
        """
        Tests that the name and description can be updated.
        """
        project = self.public_consortium.projects.create(
            name="Project 1", description="some description", owner=self.owner
        )
        serializer = ProjectSerializer(
            project, data=dict(name="New project name", description="new description")
        )
        self.assertTrue(serializer.is_valid())
        project = serializer.save()
        project.refresh_from_db()
        self.assertEqual(project.name, "New project name")
        self.assertEqual(project.description, "new description")

    def test_update_enforces_required_fields_not_blank(self):
        """
        Tests that the required fields cannot be blank on update.
        """
        project = self.public_consortium.projects.create(
            name="Project 1", description="some description", owner=self.owner
        )
        serializer = ProjectSerializer(project, data=dict(name="", description=""))
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {"name", "description"})
        for name in {"name", "description"}:
            self.assertEqual(serializer.errors[name][0].code, "blank")

    def test_update_enforces_unique_name(self):
        """
        Tests that the unique constraint is enforced for name on update.
        """
        project = self.public_consortium.projects.create(
            name="Project 1", description="some description", owner=self.owner
        )
        # Make another project with a name that we will collide with on update
        self.public_consortium.projects.create(
            name="New project name", description="some description", owner=self.owner
        )
        serializer = ProjectSerializer(
            project, data=dict(name="New project name"), partial=True
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {"name"})
        self.assertEqual(serializer.errors["name"][0].code, "unique")

    def test_cannot_update_consortium(self):
        """
        Tests that the consortium cannot be updated.
        """
        project = self.public_consortium.projects.create(
            name="Project 1", description="some description", owner=self.owner
        )
        self.assertEqual(project.consortium.pk, self.public_consortium.pk)
        # Make another valid consortium public consortium to update to
        consortium = Consortium.objects.create(
            name="Public Consortium 2",
            description="some description",
            is_public=True,
            manager=get_user_model().objects.create_user("manager3"),
        )
        serializer = ProjectSerializer(
            project, data=dict(consortium=consortium.pk), partial=True
        )
        # The validation should pass, but the consortium will not change
        self.assertTrue(serializer.is_valid())
        project = serializer.save()
        project.refresh_from_db()
        self.assertEqual(project.consortium.pk, self.public_consortium.pk)

    def test_cannot_update_status(self):
        """
        Tests that the status cannot be updated.
        """
        project = self.public_consortium.projects.create(
            name="Project 1", description="some description", owner=self.owner
        )
        self.assertEqual(project.status, Project.Status.EDITABLE)
        serializer = ProjectSerializer(
            project, data=dict(status=Project.Status.UNDER_REVIEW.name), partial=True
        )
        # The validation should pass, but the consortium will not change
        self.assertTrue(serializer.is_valid())
        project = serializer.save()
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.EDITABLE)
