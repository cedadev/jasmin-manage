from django.contrib.auth import get_user_model

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer
from rest_framework.views import APIView


class UserSerializer(ModelSerializer):
    """
    Serializer for the user of a collaborator.
    """
    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'first_name', 'last_name')


class CurrentUserView(APIView):
    """
    View to return details of the current user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, format = None):
        """
        Return information about the authenticated user.
        """
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
