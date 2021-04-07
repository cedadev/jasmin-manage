from rest_framework import mixins, viewsets

from ..exceptions import Conflict
from ..models import Comment
from ..permissions import CommentPermissions
from ..serializers import CommentSerializer


# Comments can only be listed and created via a project
class CommentViewSet(mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     mixins.DestroyModelMixin,
                     viewsets.GenericViewSet):
    """
    View set for the comment model.
    """
    permission_classes = [CommentPermissions]

    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
