=============
Customization
=============

Configuration rules
===================

Configuration is a simple flat dictionary of rules:

.. code-block:: python

    {
        '<rule_id>': {
            'comment': 'Some info about this rule. Not mandatory.',
            'type': '<nested|cartesian|words|const>',
            # additional fields, depending on type
        },
        ...
    }

``<rule_id>`` is the identifier of rule. Root rule must be named ``'all'`` - that's what you use
when you call ``generate()`` or ``generate_slug()`` without arguments.

There are four types of configuration rules.

* Word list.

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

  Length of word list is a number of words.

* Nested list.

  Chooses a random word from any of the child lists.
  Probability is proportional to child list length.

  .. code-block:: python

      # This will produce random adjective: color or taste
      'adjective': {
          'type': 'nested',
          'lists': ['color', 'taste']
      },

  Child lists can be of any type.

  Number of child lists is not limited.

  Length of nested list is combined length of all child lists.

* Constant.

  It's just a word. Useful for prepositions.

  .. code-block:: python

      'of': {
          'type': 'const',
          'value': 'of'
      },

* Cartesian_ list.

  This element works like a slot machine, and produces a list of length N
  by choosing one random word from N child lists.

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

  *NOTE: You can have many nested lists, but you should never
  put one Cartesian list inside another.*

  Length of Cartesian list is a product of lengths of child lists.

Let's try the config defined above:
::

    >>> from coolname import RandomNameGenerator
    >>> generator = RandomNameGenerator(config)
    >>> for i in range(3):
    ...     print(generator.generate_slug())
    ...
    my-banana-is-sweet
    my-apple-is-green
    my-apple-is-sour

.. _Cartesian: https://en.wikipedia.org/wiki/Cartesian_product

Length limits
=============

There are two limits:

* ``max_length``

    This constraint is hard: you can't create :class:`RandomNameGenerator` instance
    if some word in some rule exceeds that rule's limit.

    For example, this will fail:

        .. code-block:: json

            {
                "type": "words",
                "words": ["cat", "tiger", "jaguar"],
                "max_length": 5
            }

    Different word lists can have different limits.
    If you don't specify it, there is no limit.

* ``max_slug_length``

    This constraint is soft: if result is too long, it is silently discarded
    and generator rolls the dice again.
    This allows you to have longer-than-average words which
    still fit nicely with shorter words from other lists.

    Of course, it's better to keep the fraction of "too long" combinations low,
    as it affects the performance. In fact, :class:`RandomNameGenerator` performs
    a sanity test upon an initialization: if probability of getting "too long" combination
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

Both of these limits are optional. Default configuration uses ``"max_slug_length": 50``
according to Django slug length.

Configuration files
===================

Another small example: a pair of (adjective, noun) generated as follows: ::

    (crouching|hidden) (tiger|dragon)

Of course, you can just feed config dict into :class:`RandomNameGenerator` constructor:

>>> from coolname import RandomNameGenerator
>>> config = {'all': {'type': 'cartesian', 'lists': ['adjective', 'noun']}, 'adjective': {'type':'words', 'words':['crouching','hidden']}, 'noun': {'type': 'words', 'words': ['tiger', 'dragon']}}
>>> g = RandomNameGenerator(config)
>>> g.generate_slug()
'hidden-dragon'

but it becomes inconvenient as number of words grows. So, ``coolname`` can also use a mixed files format:
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

>>> from coolname.loader import load_config
>>> config = load_config('./my_config')

That's all! Now loaded config contains all the same rules and we can create a generator object:

>>> config
{'adjective': {'words': ['crouching', 'hidden'], 'type': 'words'}, 'noun': {'words': ['dragon', 'tiger'], 'type': 'words'}, 'all': {'lists': ['adjective', 'noun'], 'type': 'cartesian'}}
>>> g = RandomNameGenerator(config)
>>> g.generate_slug()
'hidden-tiger'

Text files format
-----------------

Basic format is simple: ::

    # comment
    word
    word  # inline comment

    # blank lines are OK
    word

You can also specify options like this: ::

    max_length = 13

Which is equivalent to adding the same option in config dictionary:

.. code-block:: json

    {
        "type": "words",
        "words": [...],
        "max_length": 13
    }

Options must be specified **before** words.

Unicode support
===============

Unicode is fully supported. Just use UTF-8 for the configuration files.

