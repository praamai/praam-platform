"""Platform errors."""


class PlatformError(Exception):
    """Base platform error."""


class AppNotFoundError(PlatformError):
    """Unknown app key in services.yaml."""


class SecretNotFoundError(PlatformError):
    """Secret name not registered or missing from backend."""


class SecretsBackendError(PlatformError):
    """Secrets backend misconfigured or unavailable."""
