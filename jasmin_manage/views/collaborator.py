from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Collaborator
from ..serializers import CollaboratorSerializer


class CollaboratorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View set for the collaborator model.
    """
    queryset = Collaborator.objects.all()
    serializer_class = CollaboratorSerializer
