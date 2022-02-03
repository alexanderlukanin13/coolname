=====================
Classes and functions
=====================

.. py:module:: coolname

Default generator
=================

.. py:function:: generate(pattern=None)

    Returns a random sequence as a list of strings.

    :param int pattern: Can be 2, 3 or 4.
    :rtype: list of strings

.. py:function:: generate_slug(pattern=None)

    Same as :func:`generate`, but returns a slug as a string.

    :param int pattern: Can be 2, 3 or 4.
    :rtype: str

.. py:function:: get_combinations_count(pattern=None)

    Returns the number of possible combinations.

    :param int pattern: Can be 2, 3 or 4.
    :rtype: int

.. py:function:: replace_random(random)

    Replaces the random number generator. It doesn't affect custom generators.

    :param random: :class:`random.Random` instance.

Custom generators
=================

.. py:class:: RandomGenerator(config, random=None)

    :param dict config: Custom configuration dictionary.
    :param random: :class:`random.Random` instance. If not provided, :func:`random.randrange` will be used.

    .. py:method:: generate(pattern=None)

        Returns a random sequence as a list of strings.

        :param pattern: Not applicable by default. Can be configured.
        :rtype: list of strings

    .. py:method:: generate_slug(pattern=None)

        Same as :meth:`generate`, but returns a slug as a string.

        :param pattern: Not applicable by default. Can be configured.
        :rtype: str

    .. py:method:: get_combinations_count(pattern=None)

        Returns the number of possible combinations.

        :param pattern: Not applicable by default. Can be configured.
        :rtype: int
