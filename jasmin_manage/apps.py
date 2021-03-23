from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    """
    App configuration for the JASMIN Manage app.
    """
    name = 'jasmin_manage'
    verbose_name = 'JASMIN Manage'

    def ready(self):
        # On ready, connect the signals for the notifications
        from . import notifications
