================
Parameters table
================

.. py:currentmodule:: coolname

Summary of all parameters.

✅ means that parameter acts when :py:class:`~coolname.RandomGenerator` is created:
it either configures the generator, or acts as load-time validation.
If such validation fails, :py:class:`~coolname.ConfigurationError` is raised.

🚀 means that parameter acts at runtime every time :py:meth:`~coolname.RandomGenerator.generate`
or :py:meth:`~coolname.RandomGenerator.generate_slug` is called.
It's to silently discard unwanted combinations.


.. list-table::
    :width: 100%
    :header-rows: 1

    * - Parameter
      - Scope
      - When
      - Type
      - Default value
      - Description

    * - ``allow_whitespace``
      - Words list, Phrases list, ``*.txt``
      - ✅
      - ``bool``
      - ``False``
      - Allow words or words within a phrase to contain whitespace.

    * - ``generator``
      - Any top-level list
      - ✅
      - ``bool``
      - ``False``†
      - List is a generator endpoint and can be used in :py:func:`generate`.

    * - ``ensure_unique``
      - :py:class:`RandomGenerator` instance via ``"all"`` list
      - 🚀
      - ``bool``
      - ``True``
      - Don't generate combinations with repeating words.

    * - ``ensure_unique_prefix``
      - :py:class:`RandomGenerator` instance via ``"all"`` list
      - 🚀
      - ``int | None``
      - ``None``
      - Don't generate combinations where first N symbols of any two word match,
        e.g. ``"great-fox-of-greatness"``.

    * - ``max_length``
      - Words list, Phrases list, ``*.txt``
      - ✅
      - ``int | None``
      - ``None``
      - Maximum number of characters in a word or phrase (not counting separators).

    * - ``max_slug_length``
      - :py:class:`RandomGenerator` instance via ``"all"`` list
      - 🚀
      - ``int | None``
      - ``None``
      - Don't generate slugs with total length (including separators) exceeding N.

    * - ``number_of_words``
      - Phrases list, ``*.txt``
      - ✅
      - ``int | None``
      - ``None``
      - Exact number of words in every phrase in this list.

    * - ``separator``
      - Phrases list, ``*.txt``
      - ✅
      - ``str``
      - ``r're:\s+'``
      - Separator used to split phrases defined as plain strings (not as lists/tuples). Use ``'re:'`` prefix for regular expression.

    * - ``strip_whitespace``
      - Words list, Phrases list, ``*.txt``
      - ✅
      - ``bool``
      - ``True``
      - Strip leading and trailing whitespace from phrases and words before further processing.

† Special cases where default is ``generator=True``: main ``"all"`` list and lists with integer names (such as ``"4"``).
