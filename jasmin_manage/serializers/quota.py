from ..models import Quota

from .base import BaseSerializer


class QuotaSerializer(BaseSerializer):
    """
    Serializer for the quota model.
    """
    class Meta:
        model = Quota
        fields = '__all__'

    # Disable the links field as there is no /quotas endpoint
    _links = None
