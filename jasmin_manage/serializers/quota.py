from rest_framework import serializers

from ..models import Quota, Requirement

from .base import BaseSerializer


class QuotaSerializer(BaseSerializer):
    """
    Serializer for the quota model.
    """

    class Meta:
        model = Quota
        fields = "__all__"

    # Disable the links field as there is no /quotas endpoint
    _links = None

    # Add fields for summary data
    total_provisioned = serializers.SerializerMethodField()
    total_awaiting_provisioning = serializers.SerializerMethodField()
    total_approved = serializers.SerializerMethodField()

    def get_total_provisioned(self, obj):
        return obj.get_total_for_status(Requirement.Status.PROVISIONED)

    def get_total_awaiting_provisioning(self, obj):
        return obj.get_total_for_status(Requirement.Status.AWAITING_PROVISIONING)

    def get_total_approved(self, obj):
        return obj.get_total_for_status(Requirement.Status.APPROVED)
