from rest_framework import permissions, viewsets

from ..models import Category
from ..serializers import CategorySerializer


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View set for the category model.
    """
    permission_classes = [permissions.IsAuthenticated]

    queryset = Category.objects.all().prefetch_related('resources')
    serializer_class = CategorySerializer
