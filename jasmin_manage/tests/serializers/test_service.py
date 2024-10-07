from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.test import APIRequestFactory

from ...models import Category, Consortium
from ...serializers import ServiceSerializer, ServiceListSerializer


class ServiceSerializerTestCase(TestCase):
    """
    Tests for the service serializer.
    """

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Category 1")
        cls.consortium = Consortium.objects.create(
            name="Consortium 1",
            description="some description",
            manager=get_user_model().objects.create_user("manager1"),
        )
        cls.project = cls.consortium.projects.create(
            name="Project 1",
            description="some description",
            owner=get_user_model().objects.create_user("owner1"),
        )

    def test_renders_instance_correctly(self):
        """
        Tests that the serializer renders an existing instance correctly.
        """
        # Make a service to render
        service = self.project.services.create(name="service1", category=self.category)
        # In order to render the links correctly, there must be a request in the context
        request = APIRequestFactory().post("/services/{}/".format(service.pk))
        serializer = ServiceSerializer(service, context=dict(request=request))
        # Check that the right keys are present
        self.assertCountEqual(
            serializer.data.keys(), {"id", "name", "category", "project", "_links"}
        )
        # Check the the values are correct
        # Don't explicitly check the links field - it has tests
        self.assertEqual(serializer.data["id"], service.pk)
        self.assertEqual(serializer.data["name"], service.name)
        self.assertEqual(serializer.data["category"], self.category.pk)
        self.assertEqual(serializer.data["project"], self.project.pk)

    def test_create_uses_project_from_context(self):
        """
        Tests that creating a service uses the project from the context.
        """
        serializer = ServiceSerializer(
            data=dict(name="service1", category=self.category.pk),
            context=dict(project=self.project),
        )
        self.assertTrue(serializer.is_valid())
        service = serializer.save()
        service.refresh_from_db()
        self.assertEqual(service.project.pk, self.project.pk)
        self.assertEqual(service.category.pk, self.category.pk)
        self.assertEqual(service.name, "service1")

    def test_create_enforces_required_fields(self):
        """
        Tests that required fields are enforced on create.
        """
        serializer = ServiceSerializer(data={}, context=dict(project=self.project))
        self.assertFalse(serializer.is_valid())
        required_fields = {"name", "category"}
        self.assertCountEqual(serializer.errors.keys(), required_fields)
        for name in required_fields:
            self.assertEqual(serializer.errors[name][0].code, "required")

    def test_cannot_create_with_same_category_and_name(self):
        """
        Tests that the serializer enforces the unique together constraint on category and name.
        """
        # Create an initial service
        self.project.services.create(name="service1", category=self.category)
        # Then try to create the same service using the serializer
        serializer = ServiceSerializer(
            data=dict(name="service1", category=self.category.pk),
            context=dict(project=self.project),
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["name"][0].code, "unique")

    def test_cannot_override_project_on_create(self):
        """
        Tests that the project cannot be overridden by specifying it in the input data.
        """
        # Create a project whose PK will be given in the data
        # We will specify cls.project in the context, which is the project that the
        # service should be added to
        project = self.consortium.projects.create(
            name="Project 2",
            description="some description",
            owner=get_user_model().objects.create_user("owner2"),
        )
        serializer = ServiceSerializer(
            data=dict(name="service1", category=self.category.pk, project=project.pk),
            context=dict(project=self.project),
        )
        self.assertTrue(serializer.is_valid())
        service = serializer.save()
        # Re-fetch the collaborator from the database before asserting
        service.refresh_from_db()
        # Check that the service belongs to cls.project, not the project we created
        self.assertEqual(
            len(project.services.all()), 0
        )  # This project should have no services
        self.assertEqual(len(self.project.services.all()), 1)
        self.assertEqual(service.project.pk, self.project.pk)

    def test_cannot_create_with_invalid_category(self):
        """
        Tests that an invalid category correctly fails.
        """
        serializer = ServiceSerializer(
            data=dict(name="service1", category=10), context=dict(project=self.project)
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["category"][0].code, "does_not_exist")

    def test_cannot_create_with_invalid_name(self):
        """
        Tests that an invalid name correctly fails.
        """
        # Test with a blank name
        serializer = ServiceSerializer(
            data=dict(name="", category=self.category.pk),
            context=dict(project=self.project),
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["name"][0].code, "blank")
        # Test with whitespace
        serializer = ServiceSerializer(
            data=dict(name="service 1", category=self.category.pk),
            context=dict(project=self.project),
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["name"][0].code, "invalid")
        # Test with capital letters
        serializer = ServiceSerializer(
            data=dict(name="SERVICE1", category=self.category.pk),
            context=dict(project=self.project),
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["name"][0].code, "invalid")
        # Test with unicode characters
        serializer = ServiceSerializer(
            data=dict(name="sèrvíçë1", category=self.category.pk),
            context=dict(project=self.project),
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["name"][0].code, "invalid")


class ServiceListSerializerTestCase(TestCase):
    """
    Tests for the service list serializer.
    """

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Category 1")
        cls.consortium = Consortium.objects.create(
            name="Consortium 1",
            description="some description",
            manager=get_user_model().objects.create_user("manager1"),
        )
        cls.project = cls.consortium.projects.create(
            name="Project 1",
            description="some description",
            owner=get_user_model().objects.create_user("owner1"),
        )

    def test_list_renders_instance_correctly(self):
        """
        Tests that the list serializer renders an existing instance correctly.
        """
        # Make a service to render
        service = self.project.services.create(name="service1", category=self.category)
        # In order to render the links correctly there must be a request in the context
        request = APIRequestFactory().post("/")
        serializer = ServiceListSerializer(service, context=dict(request=request))
        # Check that the right keys are present
        self.assertCountEqual(
            serializer.data.keys(),
            {
                "id",
                "name",
                "consortium",
                "has_active_requirements",
                "consortium_fairshare",
                "project_fairshare",
                "requirements",
                "category",
                "project",
                "_links",
            },
        )

    def test_list_cannot_create_with_invalid_requirement(self):
        """
        Tests that invalid requirements correctly fails for the list of services.
        """
        # Test with a string for the requirements
        serializer = ServiceListSerializer(
            data=dict(
                name="service2", category=self.category.pk, requirements="requirements1"
            ),
            context=dict(project=self.project),
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors["requirements"]["non_field_errors"][0].code, "not_a_list"
        )
        # Test with an int for the requirements
        serializer = ServiceListSerializer(
            data=dict(name="service2", category=self.category.pk, requirements=10),
            context=dict(project=self.project),
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors["requirements"]["non_field_errors"][0].code, "not_a_list"
        )
