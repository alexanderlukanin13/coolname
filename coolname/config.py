class _CONF:
    """All strings related to config, to avoid hardcoding."""

    class TYPE:
        """Node type in configuration."""
        NESTED = 'nested'
        CARTESIAN = 'cartesian'
        WORDS = 'words'
        CONST = 'const'

    class FIELD:
        """Allowed fields."""
        TYPE = 'type'
        LISTS = 'lists'
        WORDS = 'words'
        VALUE = 'value'
        GENERATOR = 'generator'
