=================
Custom generators
=================

.. py:currentmodule:: coolname

.. _configuration-rules:

Configuration rules
===================

Configuration is a flat dictionary of rules:

.. code-block:: python

    {
        '<rule_id>': {
            'comment': 'Some info about this rule. Not mandatory.',
            'type': '<nested|cartesian|words|phrases|const>',
            # additional fields, depending on type
        },
        ...
    }

``<rule_id>`` is the identifier of rule. Root rule must be named ``'all'`` - that's what you use
when you call :func:`generate` or :func:`generate_slug` without arguments.

There are five types of configuration rules.

Words list
----------

A ground-level building block. Chooses a random word from a list,
with equal probability.

.. code-block:: python

    # This will produce random color
    'color': {
        'type': 'words',
        'words': ['red', 'green', 'yellow']
    },
    # This will produce random taste
    'taste': {
        'type': 'words',
        'words': ['sweet', 'sour']
    },
    # This will produce random fruit
    'fruit': {
        'type': 'words',
        'words': ['apple', 'banana']
    },


Phrases list
------------

Same as words list, but each element is one or more words.

.. code-block:: python

    # This will produce random color
    'color': {
        'type': 'phrases',
        'words': ['red', 'green', 'navy blue', ['royal', 'purple']]
    }

Phrase can be written as a string (words are separated by space) or as a list of words.

Nested list
-----------

Chooses a random word (or phrase) from any of the child lists.
Probability is proportional to child list length.

.. code-block:: python

    # This will produce random adjective: color or taste
    'adjective': {
        'type': 'nested',
        'lists': ['color', 'taste']
    },

Child lists can be of any type.

Number of child lists is not limited.

Length of nested list is the sum of lengths of all child lists.

Constant
--------

It's just a word. Useful for prepositions.

.. code-block:: python

    'of': {
        'type': 'const',
        'value': 'of'
    },

Cartesian list
---------------

Cartesian_ list works like a slot machine, and produces a list of length N
by choosing one random word (or phrase) from every child list.

.. code-block:: python

    # This will produce a random list of 4 words,
    # for example: ['my', 'banana', 'is', 'sweet']
    'all': {
        'type': 'cartesian',
        'lists': ['my', 'fruit', 'is', 'adjective']
    },
    # Additional const definitions
    'is': {
        'type': 'const',
        'value': 'is'
    },
    'my': {
        'type': 'const',
        'value': 'my'
    },

Length of Cartesian list is the product of lengths of child lists.

Let's try the config defined above:

.. code-block:: python

    >>> from coolname import RandomGenerator
    >>> generator = RandomGenerator(config)
    >>> for i in range(3):
    ...     print(generator.generate_slug())
    ...
    my-banana-is-sweet
    my-apple-is-green
    my-apple-is-sour

.. warning::
    You can have many nested lists, but you should never put a Cartesian list inside another Cartesian list.

.. _Cartesian: https://en.wikipedia.org/wiki/Cartesian_product

Length limits
=============

Number of characters
--------------------

There are two limits:

* ``max_length``

    This constraint is hard: you can't create :class:`RandomGenerator` instance
    if some word (or phrase) in some rule exceeds that rule's limit.

    For example, this will fail:

        .. code-block:: json

            {
                "all": {
                    "type": "words",
                    "words": ["cat", "tiger", "jaguar"],
                    "max_length": 5
                }
            }

    Different word lists and phrase lists can have different limits.
    If you don't specify it, there is no limit.

    *Note: when max_length is applied to phrase lists, spaces are not counted. So this will work:*

        .. code-block:: json

            {
                "all": {
                    "type": "phrases",
                    "phrases": ["big cat"],
                    "max_length": 6
                }
            }

* ``max_slug_length``

    This constraint is soft: if result is too long, it is silently discarded
    and generator rolls the dice again.
    This allows you to have longer-than-average words (and phrases) which
    still fit nicely with shorter words (and phrases) from other lists.

    Of course, it's better to keep the fraction of "too long" combinations low,
    as it affects the performance. In fact, :class:`RandomGenerator` performs
    a sanity test upon initialization: if probability of getting "too long" combination
    is unacceptable, it will raise an exception.

    For example, this will produce 7 possible combinations,
    and 2 combinations (green-square and green-circle) will never appear
    because they exceed the max slug length:

    .. code-block:: json

        {
            "adjective": {
                "type": "words",
                "words": ["red", "blue", "green"]
            },
            "noun": {
                "type": "words",
                "words": ["line", "square", "circle"]
            },
            "all": {
                "type": "cartesian",
                "lists": ["adjective", "noun"],
                "max_slug_length": 11
            }
        }

Both of these limits are optional. Default configuration uses ``max_slug_length = 50``
according to Django slug length.

Number of words
---------------

Use ``number_of_words`` parameter to enforce particular number of words in a phrase for a given list.

This constraint is hard: you can't create :class:`RandomGenerator` instance
if some phrase in a given list has a wrong number of words.

For example, this will fail because the last item has 3 words:

.. code-block:: json
    :emphasize-lines: 8,10

    {
        "all": {
            "type": "phrases",
            "phrases": [
                "washing machine",
                "microwave oven",
                "vacuum cleaner",
                "large hadron collider"
            ],
            "number_of_words": 2
        }
    }

Configuration files
===================

Another small example: a pair of (adjective, noun) generated as follows: ::

    (crouching|hidden) (tiger|dragon)

Of course, you can just feed config dict into :class:`RandomGenerator` constructor:

.. code-block:: python

    >>> from coolname import RandomGenerator
    >>> config = {'all': {'type': 'cartesian', 'lists': ['adjective', 'noun']}, 'adjective': {'type':'words', 'words':['crouching','hidden']}, 'noun': {'type': 'words', 'words': ['tiger', 'dragon']}}
    >>> g = RandomGenerator(config)
    >>> g.generate_slug()
    'hidden-dragon'

but it becomes inconvenient as number of words grows. So, :mod:`coolname` can also use a mixed files format:
you can specify rules in JSON file, and encapsulate long word lists into separate plain txt files
(one file per one ``"words"`` rule).

For our example, we would need three files in a directory:

**my_config/config.json**

.. code-block:: json

    {
        "all": {
            "type": "cartesian",
            "lists": ["adjective", "noun"]
        }
    }

**my_config/adjective.txt** ::

    crouching
    hidden

**my_config/noun.txt** ::

    dragon
    tiger

*Note: only config.json is mandatory; you can name other files as you want.*

Use auxiliary function to load config from a directory:

.. code-block:: python

    >>> from coolname.loader import load_config
    >>> config = load_config('./my_config')

That's all! Now loaded config contains all the same rules and we can create :class:`RandomGenerator` object:

.. code-block:: python

    >>> config
    {'adjective': {'words': ['crouching', 'hidden'], 'type': 'words'}, 'noun': {'words': ['dragon', 'tiger'], 'type': 'words'}, 'all': {'lists': ['adjective', 'noun'], 'type': 'cartesian'}}
    >>> g = RandomGenerator(config)
    >>> g.generate_slug()
    'hidden-tiger'

Text file format for words
---------------------------

Basic format is simple: ::

    # comment
    one
    two  # inline comment

    # blank lines are OK
    three

You can also specify options like this: ::

    max_length = 13

Which is equivalent to adding the same option in config dictionary:

.. code-block:: python
    :emphasize-lines: 4

    {
        'type': 'words',
        'words': ['one', 'two', 'three'],
        'max_length': 13
    }

Options should be placed in the beginning of the text file, before the first word.

Text file format for phrases
-----------------------------

For phrases, format is the same as for words. If any line in a file has more than one word,
the whole file is automagically transformed to a ``"phrases"`` list instead of ``"words"``.

For example, this file: ::

    one
    two

    # Here is the phrase
    three four

is translated to the following rule:

.. code-block:: json

    {
        "type": "phrases",
        "phrases": [
            ["one"], ["two"], ["three", "four"]
        ]
    }

Unicode support
===============

Default implementation uses English, but you can create configuration in any language -
just save the config files in UTF-8 encoding.
