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
        fields = '__all__'
        read_only_fields = ('service', 'status', 'version')
        create_only_fields = ('resource', )

    status = EnumField(Requirement.Status)

    def get_extra_kwargs(self):
        extra_kwargs = super().get_extra_kwargs()
        # Use the service to limit the set of resources that are possible
        # The resource is only writable during create, so using the service from
        # the context is sufficient
        service = self.context.get('service')
        if service:
            resource_kwargs = extra_kwargs.setdefault('resource', {})
            resource_kwargs.update(queryset = service.category.resources.all())
        return extra_kwargs

    def validate_start_date(self, value):
        # When changing the start date, either creating or updating, it must be in the future
        previous = getattr(self.instance, 'start_date', None)
        if value != previous and value < date.today():
            raise serializers.ValidationError('Start date must be in the future.')
        return value

    def validate(self, data):
        # Update the validated data with the service if required
        service = self.context.get('service')
        if service:
            data.update(service = service)
        return super().validate(data)

    def create(self, validated_data):
        # Inject the project from the context when creating
        validated_data.update(service = self.context['service'])
        return super().create(validated_data)
