class ReadOnlySerializerMixin:
    """
    Mixin for serializers that makes them read-only regardless of field-level
    or serializer Meta settings.
    """
    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields

    def save(self, **kwargs):
        raise RuntimeError('Save is not permitted for read-only serializers.')


def read_only_serializer(serializer_class):
    """
    Returns a new serializer with the same fields as the given serializer but all read-only.
    """
    return type(
        f'ReadOnly{serializer_class.__name__}',
        (ReadOnlySerializerMixin, serializer_class),
        {}
    )
