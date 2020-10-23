from ..models import Consortium

from .base import BaseSerializer


class ConsortiumSerializer(BaseSerializer):
    """
    Serializer for the consortium model.
    """
    class Meta:
        model = Consortium
        fields = '__all__'
