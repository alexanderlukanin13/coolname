__version__ = '0.2.1'

# Hint: set COOLNAME_DATA_DIR and/or COOLNAME_DATA_MODULE
# before `import coolname` to change the default generator.

from .exceptions import InitializationError
from .impl import generate, generate_slug, get_combinations_count,\
    RandomGenerator, replace_random
