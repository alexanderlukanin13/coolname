from ._version import __version__, __version_tuple__

# Hint: set COOLNAME_DATA_DIR and/or COOLNAME_DATA_MODULE
# before `import coolname` to change the default generator.

from .exceptions import InitializationError, ConfigurationError
from .impl import generate, generate_slug, get_combinations_count,\
    RandomGenerator, replace_random

__all__ = [
    'generate', 'generate_slug', 'get_combinations_count', 'replace_random',
    'RandomGenerator',
    'InitializationError', 'ConfigurationError',
]
