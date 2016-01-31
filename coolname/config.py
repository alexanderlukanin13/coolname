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

    # 11 letters limitation is to fit 4 words into Django slug (max_length=50)
    MAX_WORD_LENGTH = 11
