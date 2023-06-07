from rest_framework import permissions, viewsets

from ..models import Category
from ..serializers import CategorySerializer
from .base import BaseViewSet


class CategoryViewSet(BaseViewSet,viewsets.ReadOnlyModelViewSet):
    """
    View set for the category model.
    """
    permission_classes = [permissions.IsAuthenticated]

    queryset = Category.objects.all().prefetch_related('resources')
    serializer_class = CategorySerializer
