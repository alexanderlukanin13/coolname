#!/usr/bin/env python

from setuptools import setup, Command
from setuptools.command.build import build


# Compile default config from *.txt files. Initially it was to support packaging in *.egg (obsolete & unsupported).
# Nowadays, it's not required in most (all?) scenarios, loading from *.txt would work just fine.
# We keep it just in case.
# It may have slight performance advantage due to reading only one *.py file vs 10+ *.txt files.
#
# Historical comment:
# ---------
# All this magic is needed to support packaging in zip/egg.
# Reading files inside zip is problematic, so we compile
# everything into config dict and stuff it into
# coolname/data/__init__.py.
# ---------
def compile_init_py():
    import os
    import sys
    current_path = os.path.dirname(__file__)
    current_path_appended = False
    if current_path not in sys.path:
        sys.path.append(current_path)
        current_path_appended = True
    from coolname.loader import load_config
    if current_path_appended:
        sys.path.remove(current_path)
    config_path = os.path.join(current_path, 'coolname', 'data')
    config = load_config(config_path)
    # Write to data/__init__.py to be used from .egg
    with open(os.path.join(config_path, '__init__.py'), 'w', encoding='utf-8') as file:
        file.write(f'''# THIS FILE IS AUTO-GENERATED, DO NOT EDIT
config = {config!r}
''')


class GenerateData(Command):

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        compile_init_py()


class CustomBuild(build):
    sub_commands = [
        ('generate_data', None),
        *build.sub_commands
    ]


setup(
    cmdclass={'build': CustomBuild, 'generate_data': GenerateData},
)
