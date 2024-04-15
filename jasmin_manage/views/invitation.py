from rest_framework import mixins, viewsets

from ..models import Invitation
from ..permissions import InvitationPermissions
from ..serializers import InvitationSerializer


# Invitations can only be listed and created via a project
# They also cannot be updated via the API, only deleted
class InvitationViewSet(
    mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    """
    View set for the invitation model.
    """

    permission_classes = [InvitationPermissions]

    queryset = Invitation.objects.all()
    serializer_class = InvitationSerializer
