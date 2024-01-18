from datetime import date

from rest_framework import serializers

from ..models import Requirement

from .base import BaseSerializer, EnumField


class RequirementSerializer(BaseSerializer):
    """
    Serializer for the requirement model.
    """

    class Meta:
        model = Requirement
        fields = "__all__"
        read_only_fields = ("service",)
        create_only_fields = ("resource",)

    status = EnumField(Requirement.Status, read_only=True)
    # The min_value constraint is not populated automatically by virtue of being a PositiveIntegerField
    # So take the opportunity to prevent it from going to 0 as well
    amount = serializers.IntegerField(min_value=1)

    def get_extra_kwargs(self):
        extra_kwargs = super().get_extra_kwargs()
        # Use the service to limit the set of resources that are possible
        # The resource is only writable during create, so using the service from
        # the context is sufficient
        service = self.context.get("service")
        if service:
            resource_kwargs = extra_kwargs.setdefault("resource", {})
            resource_kwargs.update(queryset=service.category.resources.all())
        return extra_kwargs

    def validate_start_date(self, value):
        # When changing the start date, either creating or updating, it must be in the future
        previous = getattr(self.instance, "start_date", None)
        if value != previous and value < date.today():
            raise serializers.ValidationError(
                "Start date must be in the future.", "date_in_past"
            )
        return value

    def validate(self, data):
        validated_data = super().validate(data)
        # Check that the end date is after the start date
        # We need to check this if either the start or end date is changing
        if "start_date" in validated_data or "end_date" in validated_data:
            # The start date must come either from the data or the instance
            if "start_date" in validated_data:
                start_date = validated_data["start_date"]
            elif self.instance:
                start_date = self.instance.start_date
            else:
                start_date = Requirement._meta.get_field("start_date").get_default()
            # Same for end date
            if "end_date" in validated_data:
                end_date = validated_data["end_date"]
            elif self.instance:
                end_date = self.instance.end_date
            else:
                end_date = Requirement._meta.get_field("end_date").get_default()
            if end_date <= start_date:
                raise serializers.ValidationError(
                    {"end_date": "End date must be after start date."},
                    "before_start_date",
                )
        return validated_data

    def create(self, validated_data):
        # Inject the service from the context into the model
        validated_data.update(service=self.context["service"])
        return super().create(validated_data)
