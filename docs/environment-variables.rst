=====================
Environment variables
=====================

.. py:currentmodule:: coolname

You can replace the default generator using one or both following variables:

.. code-block:: bash

    export COOLNAME_DATA_DIR=some/path
    export COOLNAME_DATA_MODULE=some.module

If *any* of these is set and not empty, default generator is not created (saving memory),
and your custom generator is used instead.

``COOLNAME_DATA_DIR``
=====================

It must be a valid path (absolute or relative) to the directory with ``config.json`` and ``*.txt`` files.

``COOLNAME_DATA_MODULE``
========================

It must be a valid module name, importable from the current Python environment.

It must contain a variable named ``config``, which is a dictionary (see :ref:`configuration-rules`).

Adjust :py:data:`sys.path` (or ``PYTHONPATH``) if your module fails to import.

Precedence
==========

1. If ``COOLNAME_DATA_DIR`` is defined and not empty, *and the directory exists*, it is used.

2. If ``COOLNAME_DATA_MODULE`` is defined and not empty, it is used.

3. Otherwise, :py:class:`ImportError` is raised.

The reason for this order is to support packaging in egg files.
If you don't care about eggs, use only ``COOLNAME_DATA_DIR`` because it's more efficient and easier to maintain.
