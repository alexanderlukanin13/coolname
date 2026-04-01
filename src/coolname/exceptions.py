"""
Do not import anything directly from this module.
"""


class InitializationError(Exception):
    """Custom exception for all generator initialization errors."""
    pass


class ConfigurationError(InitializationError):
    """Specific exception for invalid configuration."""

    def __init__(self, msg: str):
        super(ConfigurationError, self).__init__(f'Invalid config: {msg}')
