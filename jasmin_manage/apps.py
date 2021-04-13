from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    """
    App configuration for the JASMIN Manage app.
    """
    name = 'jasmin_manage'
    verbose_name = 'JASMIN Manage'

    # By default, use bigints for the id field
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        # On ready, connect the signals for the notifications
        from . import notifications
