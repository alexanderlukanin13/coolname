#!/usr/bin/env python
import re

try:
    from setuptools import setup
    from setuptools.command.sdist import sdist
except ImportError:
    from distutils.core import setup
    from distutils.command.sdist import sdist


# All this magic is needed to support packaging in zip/egg.
# Reading files inside zip is problematic, so we compile
# everything into config dict and stuff it into
# coolname/data/__init__.py.
def compile_init_py():
    import codecs
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
    with codecs.open(os.path.join(config_path, '__init__.py'), 'w', encoding='utf-8') as file:
        file.write(f'''# THIS FILE IS AUTO-GENERATED, DO NOT EDIT
config = {config!r}
''')


def customize(cls):
    _old_run = cls.run
    def run(self, *args, **kwargs):
        compile_init_py()
        return _old_run(self, *args, **kwargs)
    cls.run = run
    return cls


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')
    history = history[:history.find('0.2.0')] + '''
For earlier releases, see `History <https://coolname.readthedocs.io/en/latest/history.html>`_
'''
    history = re.sub(r':\w+:`(\w+(?:\.\w+)*)`', r'``\1``', history)


test_requirements = []

setup(
    name='coolname',
    version='2.1.0',
    description="Random name and slug generator",
    long_description=readme + '\n\n' + history,
    author="Alexander Lukanin",
    author_email='alexander.lukanin.13@gmail.com',
    url='https://github.com/alexanderlukanin13/coolname',
    packages=[
        'coolname',
        'coolname.data',
    ],
    package_dir={
        'coolname': 'coolname'
    },
    cmdclass={'sdist': customize(sdist)},
    include_package_data=True,
    entry_points={'console_scripts': ['coolname = coolname.__main__:main']},
    license="BSD",
    zip_safe=True,
    keywords='coolname',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
