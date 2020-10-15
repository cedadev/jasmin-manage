from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Category, Resource
from ..serializers import CategorySerializer, ResourceSerializer


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View set for the category model.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    @action(detail = True, methods = ['GET'])
    def resources(self, request, pk = None):
        """
        Returns the resources for the category.
        """
        queryset = Resource.objects.filter(category = pk)
        context = self.get_serializer_context()
        serializer = ResourceSerializer(queryset, many = True, context = context)
        return Response(serializer.data)
