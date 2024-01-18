from rest_framework import serializers, status
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Invitation
from ..serializers import ProjectSerializer


class InvalidInvitationCode(APIException):
    """
    Raised when an invalid invitation code is given.
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = (
        "Invitation code is not valid - it may have expired or been used before."
    )
    default_code = "invalid_invitation_code"


class ProjectJoinSerializer(serializers.Serializer):
    """
    Serializer for extracting an invitation code from a request.
    """

    code = serializers.CharField()


class ProjectJoinView(APIView):
    """
    View to accept an invitation to join a project.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        """
        Accept an invitation to join a project by submitting the invitation code.
        """
        serializer = ProjectJoinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Try to find the invitation using the code we were given
        try:
            invitation = Invitation.objects.get(code=serializer.validated_data["code"])
        except Invitation.DoesNotExist:
            # If we can't locate it, return an error response
            raise InvalidInvitationCode()
        # If we did find an invitation, accept it as the logged in user
        invitation.accept(request.user)
        # Return the representation of the project that we just joined
        project_serializer = ProjectSerializer(
            invitation.project, context=dict(request=request, view=self)
        )
        return Response(project_serializer.data)

    def get_serializer(self, **kwargs):
        """
        Return the serializer for the browsable API.
        """
        return ProjectJoinSerializer(**kwargs)
