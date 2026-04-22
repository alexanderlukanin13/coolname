class InitializationError(Exception):
    """
    Base exception class for all coolname initialization errors
    (configuration files are missing, file reading error, etc.)
    """


class ConfigurationError(InitializationError):
    """
    Subclass of :py:class:`~coolname.exceptions.InitializationError`,
    raised when coolname configuration is invalid.
    """

    def __init__(self, msg: str):
        super(ConfigurationError, self).__init__(f'Invalid config: {msg}')
