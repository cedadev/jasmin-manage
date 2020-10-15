from rest_framework import viewsets

from ..models import Quota
from ..serializers import QuotaSerializer


class QuotaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View set for the resource model.
    """
    queryset = Quota.objects.all()
    serializer_class = QuotaSerializer
