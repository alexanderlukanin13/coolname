======================
Advanced customization
======================

.. py:currentmodule:: coolname

Whitespaces and separators
==========================

By default, word lists and phrase lists strip leading/trailing whitespace.
Whitespace in the middle of a word is not allowed and raises an exception.
If you want to keep whitespace as an integral part of a word, or use separator other than whitespace in a phrase,
this chapter describes how to achieve it.

In this chapter, "whitespace" means one or more spaces (ordinary or special), tabs and end-of-line characters.
Basically, any characters ``str.strip()`` strips and ``re.findall(r'\s+', ...)`` detects.
See `Unicode characters with property White_Space=yes <https://en.wikipedia.org/wiki/Whitespace_character#Unicode>`_
for a complete list.

Three relevant configuration parameters in word and phrase lists and their default values are:

.. code-block:: python

        {
           ...,
           # Strip leading and trailing whitespaces from each item
           # before further processing
           'strip_whitespace': True,

           # Allow whitespaces anywhere in a word
           # (if False, raises exception)
           'allow_whitespace': False,

           # How to split phrases defined as plain strings
           # (in JSON/Python as str, or in *.txt).
           # "re:" prefix means regular expression
           'separator': 're:\s+',
        }

Words list
----------

By default, leading and trailing whitespaces are stripped, and whitespaces in the middle are forbidden.
You can change it by adding following parameters to the words list:

.. code-block:: python

    {
        'type': 'words',
        'words': ['apple', ' banana ', 'pickled cucumber'],
        'strip_whitespace': False,  # yields ' banana ' with spaces
        'allow_whitespace': True,   # allows ' banana ' and 'pickled cucumber'
    }


When words are loaded from a ``*.txt`` file, end-of-line characters are stripped regardless of ``strip_whitespace``.

You can set ``strip_whitespace = False`` in a  ``*.txt`` file, but it's not recommended as it's very easy to make mistakes.

Here's how these parameters interact:

.. list-table::
    :width: 100%
    :widths: 25 20 20 25 10
    :header-rows: 1

    * - Word
      - ``allow_whitespace``
      - ``strip_whitespace``
      - Result
      - Default?
    * - ``' cat '``
      - ``False``
      - ``True``
      - ``'cat'``
      - Default
    * - ``' cat '``
      - ``False``
      - ``False``
      - ❌
      -
    * - ``' cat '``
      - ``True``
      - ``False``
      - ``' cat '``
      -
    * - ``' cat '``
      - ``True``
      - ``True``
      - ``'cat'``
      -
    * - ``' big cat '``
      - ``False``
      - ``True``
      - ❌
      - Default
    * - ``' big cat '``
      - ``False``
      - ``False``
      - ❌
      -
    * - ``' big cat '``
      - ``True``
      - ``False``
      - ``' big cat '``
      -
    * - ``' big cat '``
      - ``True``
      - ``True``
      - ``'big cat'``
      -

Note that a word with spaces is still a single *word*, not a *phrase* (see below).
Space will always remain (imagine a white rectangle ▯ as a special letter, instead of a genuine empty break
between words), so your slugs may look like this:

.. code-block::

    graceful-nice-big cat

Phrases list
------------

Here things get a bit more complicated. If phrases are in a ``*.txt`` file, or if they are defined in config
as plain strings (as opposed to lists or tuples), they are transformed into lists first:

1. Strip whitespace from the whole phrase if ``strip_whitespace=True``.
2. If empty, return empty list (this will raise exception)
3. Split by separator. Default separator is one or more consequitive whitespaces - same as ``separator=r're:\s+'``.

.. code-block::

    # strip_whitespace=True
    ' big cat ' ➡ ['big', 'cat']

    # strip_whitespace=True, separator='/'
    # this will raise exception down the line if allow_whitespace=False
    ' big cat / little dog ' ➡ ['big cat', 'little dog']

If phrases in config are defined in JSON or in Python code as lists of strings or tuples of strings,
not as plain strings, the splitting described above is not applicable.

Then ``strip_whitespace`` and ``allow_whitespace`` are applied to every word in a phrase individually.
Algorithm is the same as with word lists, see previous section.

.. code-block::

    # strip_whitespace=True, allow_whitespace=True
    # single phrase as a list/tuple:
    ['amazing ', ' big cat '] ➡ ('amazing', 'big cat')

    # strip_whitespace=True
    # single phrase as a plain string: strip+split+strip
    ' amazing big cat ' ➡ ('amazing', 'big', 'cat')

    # Caveat: dangling separator in the start or end of string is forbidden
    # strip_whitespace=False
    ' amazing big cat ' ➡ ['', 'amazing', 'big', 'cat', ''] ➡ ❌
    # separator='/'
    '/amazing/big/cat/' ➡ ['', 'amazing', 'big', 'cat', ''] ➡ ❌


Parameters table
================

.. list-table::
    :width: 100%
    :header-rows: 1

    * - Parameter
      - Scope
      - Type
      - Default value
      - Description

    * - ``allow_whitespace``
      - Words or Phrases list, ``*.txt``
      - ``bool``
      - ``False``
      - Allow words or words within a phrase to contain whitespace.

    * - ``generator``
      - Any top-level list
      - ``bool``
      - ``False``†
      - List is a generator endpoint and can be used in :py:func:`generate`.

    * - ``ensure_unique``
      - :py:class:`RandomGenerator` instance via ``"all"`` list
      - ``bool``
      - ``True``
      - Don't generate combinations with repeating words

    * - ``ensure_unique_prefix``
      - :py:class:`RandomGenerator` instance via ``"all"`` list
      - ``int | None``
      - ``None``
      - Don't generate combinations where first N symbols of any two word match,
        e.g. ``"great-fox-of-greatness"``

    * - ``max_length``
      - Words or Phrases list, ``*.txt``
      - ``int | None``
      - ``None``
      - Maximum number of characters in a word or phrase (not counting separators)

    * - ``max_slug_length``
      - :py:class:`RandomGenerator` instance via ``"all"`` list
      - ``int | None``
      - ``None``
      - Maximum number of characters in a slug, including separators

    * - ``number_of_words``
      - Phrases list, ``*.txt``
      - ``int | None``
      - ``None``
      - Exact number of words in a phrase

    * - ``separator``
      - Phrases list, ``*.txt``
      - ``str``
      - ``r're:\s+'``
      - Separator used to split phrases defined as plain strings. Use ``'re:'`` prefix for regular expression.

    * - ``strip_whitespace``
      - Words or Phrases list, ``*.txt``
      - ``bool``
      - ``True``
      - Strip leading and trailing whitespace from phrases and words before further processing.

† Special cases where default is ``generator=True``: main ``"all"`` list and lists with integer names (such as ``"4"``).
Excerpt from default configuration (v4.1.0), these lists are implicitly generators:

.. code-block:: text

    {
        "all": {
            "comment": "Entry point",
            "type": "nested",
            "lists": ["2", "3", "4"],
            "ensure_unique": true,
            "ensure_unique_prefix": 4,
            "max_slug_length": 50
        },
        "2": {
            "comment": "Two words (may also contain prepositions)",
            "type": "nested",
            "lists": ["an"]
        },
        ...
