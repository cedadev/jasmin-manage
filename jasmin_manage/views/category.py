from rest_framework import mixins, viewsets

from ..models import Category, Resource
from ..serializers import CategorySerializer, ResourceSerializer


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View set for the category model.
    """
    queryset = Category.objects.all().prefetch_related('resources')
    serializer_class = CategorySerializer


class CategoryResourcesViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    View set for listing the resources for a category.
    """
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer

    def get_queryset(self):
        # Filter the resources by category
        return super().get_queryset().filter(category = self.kwargs['category_pk'])
