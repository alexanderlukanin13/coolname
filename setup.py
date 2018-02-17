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
    # Eliminate u'' literals if setup.py is executed from Python 2
    def _to_str(obj):
        if isinstance(obj, dict):
            return {str(x): _to_str(y) for x, y in obj.items()}
        elif isinstance(obj, list):
            return [_to_str(x) for x in obj]
        elif isinstance(obj, tuple):
            return tuple(str(x) for x in obj)
        elif obj.__class__.__name__ == 'unicode':
            return str(obj)
        else:
            return obj
    config = _to_str(config)
    # Write to data/__init__.py to be used from .egg
    with codecs.open(os.path.join(config_path, '__init__.py'), 'w', encoding='utf-8') as file:
        file.write(_INIT_TEMPLATE.format(config))


_INIT_TEMPLATE = '''
# THIS FILE IS AUTO-GENERATED, DO NOT EDIT
config = {!r}
# Python 2 compatibility - all words must be unicode
# (this is to make Python 2 and 3 both work from the same __init__.py code)
try:
    for listdef in config.values():
        if listdef['type'] == 'words':
            listdef['words'] = [unicode(x) for x in listdef['words']]
        elif listdef['type'] == 'phrases':
            listdef['phrases'] = [tuple(unicode(y) for y in x) for x in listdef['phrases']]
        elif listdef['type'] == 'const':
            listdef['value'] = unicode(listdef['value'])
except NameError:
    pass
'''.lstrip()


def customize(cls):
    _old_run = cls.run
    def run(self, *args, **kwargs):
        compile_init_py()
        return _old_run(self, *args, **kwargs)
    cls.run = run
    return cls


cmdclass = {
    'sdist': customize(sdist)
}


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')
    history = history[:history.find('0.2.0')] + '''
For earlier releases, see `History <https://coolname.readthedocs.io/en/latest/history.html>`_
'''
    history = re.sub(r':\w+:`(\w+(?:\.\w+)*)`', r'``\1``', history)

requirements = [
    # No setup requirements
]

test_requirements = [
    'mock',
    'six'
]

setup(
    name='coolname',
    version='1.0.4',
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
    cmdclass=cmdclass,
    include_package_data=True,
    install_requires=requirements,
    license="BSD",
    zip_safe=True,
    keywords='coolname',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
