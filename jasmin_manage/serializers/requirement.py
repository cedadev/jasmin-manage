from ..models import Requirement

from .base import BaseSerializer, EnumField


class RequirementSerializer(BaseSerializer):
    """
    Serializer for the requirement model.
    """
    class Meta:
        model = Requirement
        fields = '__all__'

    status = EnumField(Requirement.Status)
