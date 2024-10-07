from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, force_authenticate

from ...models import Consortium
from ...serializers import ConsortiumSerializer


class ConsortiumSerializerTestCase(TestCase):
    """
    Tests for the consortium serializer.
    """

    def test_renders_instance_correctly(self):
        """
        Tests that the serializer renders an existing instance correctly.
        """
        # Create a consortium
        consortium = Consortium.objects.create(
            name="Consortium 1",
            description="Some description.",
            is_public=True,
            manager=get_user_model().objects.create_user("manager1"),
        )
        # Add some projects
        for i in range(10):
            consortium.projects.create(
                name=f"Project {i}",
                description="Some description.",
                owner=get_user_model().objects.create_user(f"owner{i}"),
            )
        # Serialize the consortium
        # In order to render the links correctly, there must be a request in the context
        request = APIRequestFactory().get("/consortia/{}/".format(consortium.pk))
        # In order for the num_projects_current_user to get populated properly, we need to authenticate the request
        # Pick the first user that owns a project in the consortium
        user = consortium.projects.first().collaborators.first().user
        force_authenticate(request, user)
        serializer = ConsortiumSerializer(
            consortium, context=dict(request=Request(request))
        )
        # Check that the right keys are present
        self.assertCountEqual(
            serializer.data.keys(),
            {
                "id",
                "name",
                "description",
                "is_public",
                "manager",
                "num_projects",
                "num_projects_current_user",
                "fairshare",
                "_links",
            },
        )
        # Check the the values are correct
        # Don't explicitly check the links field - it has tests
        self.assertEqual(serializer.data["id"], consortium.pk)
        self.assertEqual(serializer.data["name"], consortium.name)
        self.assertEqual(serializer.data["description"], consortium.description)
        self.assertEqual(serializer.data["is_public"], True)
        self.assertEqual(serializer.data["num_projects"], 10)
        self.assertEqual(serializer.data["num_projects_current_user"], 1)
        # Check that the user nested dict has the correct shape
        self.assertCountEqual(
            serializer.data["manager"].keys(),
            {"id", "username", "first_name", "last_name"},
        )
        self.assertEqual(serializer.data["manager"]["id"], consortium.manager.pk)
        self.assertEqual(
            serializer.data["manager"]["username"], consortium.manager.username
        )
        self.assertEqual(
            serializer.data["manager"]["first_name"], consortium.manager.first_name
        )
        self.assertEqual(
            serializer.data["manager"]["last_name"], consortium.manager.last_name
        )
