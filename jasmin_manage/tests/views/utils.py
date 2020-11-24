import json

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APITestCase, APIRequestFactory

from ...models import Collaborator


class TestCase(APITestCase):
    """
    Base class for viewset test cases providing helper methods.
    """
    def authenticate(self, user = None):
        """
        Authenticate the test client as the given user, or a newly created user if not given.
        """
        # Make the user if required
        user = user or get_user_model().objects.create_user('testuser')
        # Authenticate the test client
        self.client.force_authenticate(user = user)
        return user

    def authenticateAsProjectCollaborator(self, project, user, role):
        """
        Authenticate the test client as a collaborator of the given project with the given role.
        """
        # Make the user if required
        user = self.authenticate(user)
        # Create the collaborator record
        project.collaborators.create(user = user, role = role)

    def authenticateAsProjectContributor(self, project, user = None):
        """
        Authenticate the test client as a contributor for the given project.
        """
        self.authenticateAsProjectCollaborator(project, user, Collaborator.Role.CONTRIBUTOR)

    def authenticateAsProjectOwner(self, project, user = None):
        """
        Authenticate the test client as an owner for the given project.
        """
        self.authenticateAsProjectCollaborator(project, user, Collaborator.Role.OWNER)

    def authenticateAsConsortiumManager(self, consortium):
        """
        Authenticate the test client as the consortium manager for the given consortium.
        """
        self.authenticate(consortium.manager)

    def assertAllowedMethods(self, endpoint, allowed_methods):
        """
        Asserts that the allowed methods for the given endpoint are as specified.
        """
        response = self.client.options(endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(method.strip() for method in response['allow'].split(',')),
            set(allowed_methods)
        )

    def assertListResponseMatchesQuerySet(self, endpoint, queryset, serializer_class):
        """
        Asserts that the response data for the given list endpoint matches the given
        queryset serialized with the given serializer class.
        """
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        serializer = serializer_class(
            queryset,
            many = True,
            context = dict(request = APIRequestFactory().get(endpoint))
        )
        self.assertEqual(response.data, serializer.data)

    def assertListResponseEmpty(self, endpoint):
        """
        Asserts that the response data for the given list endpoint is an empty list.
        """
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def assertDetailResponseMatchesInstance(self, endpoint, instance, serializer_class):
        """
        Asserts that the response data for the given detail endpoint matches the
        given instance serialized with the given serializer class.
        """
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        serializer = serializer_class(
            instance,
            context = dict(request = APIRequestFactory().get(endpoint))
        )
        self.assertEqual(response.data, serializer.data)

    def assertCreateResponseMatchesCreatedInstance(self, endpoint, data, serializer_class):
        """
        Asserts that a created instance is correctly created and that the response
        data matches the created instance.
        """
        response = self.client.post(endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Load the instance from the database as specified by the id in the response data
        instance = serializer_class.Meta.model.objects.get(pk = response.data['id'])
        serializer = serializer_class(
            instance,
            context = dict(request = APIRequestFactory().get(endpoint))
        )
        self.assertEqual(response.data, serializer.data)
        return instance

    def assertCreateResponseIsBadRequest(self, endpoint, data):
        """
        Asserts that a create with bad data results in a bad request response.
        """
        response = self.client.post(endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Return the actual parsed JSON, rather than the raw serializer data as that
        # has the weird ErrorDetail strings in
        return json.loads(response.content)

    def assertUpdateResponseMatchesUpdatedInstance(self, endpoint, instance, data, serializer_class):
        """
        Asserts that an update to an instance is correctly applied and that the response
        data matches the updated instance.
        """
        response = self.client.patch(endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Refresh the instance before comparing the response data
        instance.refresh_from_db()
        serializer = serializer_class(
            instance,
            context = dict(request = APIRequestFactory().get(endpoint))
        )
        self.assertEqual(response.data, serializer.data)
        return instance

    def assertUpdateResponseIsBadRequest(self, endpoint, data):
        """
        Asserts that an update with bad data results in a bad request response.
        """
        response = self.client.patch(endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Return the actual parsed JSON, rather than the raw serializer data as that
        # has the weird ErrorDetail strings in
        return json.loads(response.content)

    def assertDeleteResponseIsEmpty(self, endpoint):
        """
        Asserts that a delete response is empty.
        """
        response = self.client.delete(endpoint)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.content, b'')

    def assertActionResponseMatchesUpdatedInstance(self, endpoint, instance, serializer_class):
        """
        Asserts that executing an action on an instance is correctly applied and that the response
        data matches the updated instance.
        """
        response = self.client.post(endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Refresh the instance before comparing the response data
        instance.refresh_from_db()
        serializer = serializer_class(
            instance,
            context = dict(request = APIRequestFactory().get(endpoint))
        )
        self.assertEqual(response.data, serializer.data)
        return instance

    def assertNotFound(self, endpoint, method = "GET", data = None):
        """
        Asserts that the given endpoint returns a not found response.
        """
        response = getattr(self.client, method.lower())(endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def assertMethodNotAllowed(self, endpoint, method):
        """
        Asserts that the given method is not allowed for the given endpoint.
        """
        response = getattr(self.client, method.lower())(endpoint)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def assertConflict(self, endpoint, method = "GET", data = None):
        """
        Asserts that the given endpoint produces a conflict response when called with the
        given method and data.
        """
        response = getattr(self.client, method.lower())(endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        # Return the actual parsed JSON, rather than the raw serializer data as that
        # has the weird ErrorDetail strings in
        return json.loads(response.content)

    def assertPermissionDenied(self, endpoint, method = "GET", data = None):
        """
        Asserts that the given endpoint produces a permission denied response when called
        with the given method and data.
        """
        response = getattr(self.client, method.lower())(endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def assertUnauthorized(self, endpoint, method = "GET", data = None):
        """
        Asserts that the given endpoint produces an unauthorized response when called
        with the given method and data.
        """
        response = getattr(self.client, method.lower())(endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
