from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

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
            name = 'Consortium 1',
            description = 'Some description.',
            manager = get_user_model().objects.create_user('manager1')
        )
        # Serialize the consortium
        # In order to render the links correctly, there must be a request in the context
        request = APIRequestFactory().post('/consortia/{}/'.format(consortium.pk))
        serializer = ConsortiumSerializer(consortium, context = dict(request = Request(request)))
        # Check that the right keys are present
        self.assertCountEqual(serializer.data.keys(), {'id', 'name', 'description', 'manager', '_links'})
        # Check the the values are correct
        # Don't explicitly check the links field - it has tests
        self.assertEqual(serializer.data['id'], consortium.pk)
        self.assertEqual(serializer.data['name'], consortium.name)
        self.assertEqual(serializer.data['description'], consortium.description)
        # Check that the user nested dict has the correct shape
        self.assertCountEqual(serializer.data['manager'].keys(), {'id', 'username', 'first_name', 'last_name'})
        self.assertEqual(serializer.data['manager']['id'], consortium.manager.pk)
        self.assertEqual(serializer.data['manager']['username'], consortium.manager.username)
        self.assertEqual(serializer.data['manager']['first_name'], consortium.manager.first_name)
        self.assertEqual(serializer.data['manager']['last_name'], consortium.manager.last_name)
