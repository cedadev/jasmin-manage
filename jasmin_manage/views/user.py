from django.contrib.auth import get_user_model

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class CurrentUserView(APIView):
    """
    View to return details of the current user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, format = None):
        """
        Return information about the authenticated user.
        """
        data = {
            'id': request.user.id,
            'username': request.user.username,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
        }
        # If the request is impersonated, set a flag on the response
        # If the request is impersonated, just don't set the flag
        if getattr(request, 'impersonator', None):
            data.update(is_impersonated = True)
        return Response(data)
