# NOTE: this is tested via pytest, but most importantly, via tox+mypy

def test_import() -> None:
    from coolname import (
        generate, generate_slug,
        get_combinations_count, replace_random,
        RandomGenerator,
        InitializationError, ConfigurationError
    )
    from coolname.exceptions import InitializationError, ConfigurationError  # this is also fine
    from coolname.loader import load_config  # rarely needed
    from coolname.types import CoolnameConfigT, RandomT, RandomSeedArgT  # only these types are exported
