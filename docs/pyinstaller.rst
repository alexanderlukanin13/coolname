.. _pyinstaller:

.. py:currentmodule:: coolname

======================
Using with PyInstaller
======================

To create an executable with :pypi:`PyInstaller <pyinstaller>`, explicitly specify the coolname data
module as follows:

.. code-block:: bash

    pyinstaller myscript.py --hidden-import coolname.data

Or add it to a `spec file <https://pyinstaller.org/en/stable/spec-files.html>`__.

If you don't, you will see an error at runtime like this:

.. code-block:: bash

    Traceback (most recent call last):
      File "myscript.py", line 1, in <module>
        from coolname import generate_slug
      File "pyimod02_importers.py", line 457, in exec_module
      File "coolname/__init__.py", line 7, in <module>
      File "pyimod02_importers.py", line 457, in exec_module
      File "coolname/impl.py", line 639, in <module>
      File "coolname/impl.py", line 631, in _create_default_generator
      File "importlib/__init__.py", line 88, in import_module
    ModuleNotFoundError: No module named 'coolname.data'
    [PYI-12311:ERROR] Failed to execute script 'myscript' due to unhandled exception!
