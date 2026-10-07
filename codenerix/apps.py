from django.apps import AppConfig


class MyAppConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "codenerix"

    def ready(self) -> None:
        # Registered here, not via @register at import, so the import is actually used
        from django.core.checks import register

        from codenerix.checks import check_debug_toolbar_access

        register(check_debug_toolbar_access)
