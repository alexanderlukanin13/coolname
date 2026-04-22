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
      - Words list, Phrases list, ``*.txt``, Constant list; ``"all"`` list as a fallback [#f1]_
      - ✅
      - ``bool``
      - ``False``
      - Allow words or words within a phrase to contain whitespace.

    * - ``generator``
      - Any top-level list
      - ✅
      - ``bool``
      - ``False`` [#f2]_
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
      - Phrases list, ``*.txt``; ``"all"`` list as a fallback [#f1]_
      - ✅
      - ``str``
      - ``r're:\s+'``
      - Separator used to split phrases defined as plain strings (not as lists/tuples). Use ``'re:'`` prefix for regular expression.

    * - ``strip_whitespace``
      - Words list, Phrases list, ``*.txt``; ``"all"`` list as a fallback [#f1]_
      - ✅
      - ``bool``
      - ``True``
      - Strip leading and trailing whitespace from phrases and words before further processing.

    * - ``word_regex``
      - Words list, Phrases list, ``*.txt``, Constant list; ``"all"`` list as a fallback [#f1]_
      - ✅
      - ``str``
      - ``r'\w+'``
      - Regex to validate all words. Default: any Unicode letters, numbers, underscore. [#f3]_

.. rubric:: Footnotes

.. [#f1] ``strip_whitespace``, ``allow_whitespace``, ``separator`` and ``word_regex`` can be defined at ``"all"`` level
    (affects all Word/Phrase/Constant lists, lower precedence) or at individual list level (higher precedence).

.. [#f2] Special cases where default is ``generator=True``: main ``"all"`` list and lists with integer names (such as ``"4"``).

.. [#f3] If ``allow_whitespace=True``, then ``word_regex`` is applied only to non-whitespace parts of the word.
    You can include whitespace in the regex in such configuration (like ``[a-z ]+``),
    but you don't have to (``[a-z]+`` is fine).
