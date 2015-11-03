#!/usr/bin/env python


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
    print(sys.argv[1])
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
    with codecs.open(os.path.join(config_path, '__init__.py'), 'w', encoding='utf-8') as file:
        file.write('# -*- coding: utf-8 -*-\n')
        file.write('# THIS FILE IS AUTO-GENERATED, DO NOT EDIT\n')
        file.write('config = ' + repr(config) + '\n')


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

requirements = [
    # No setup requirements
]

test_requirements = [
    'mock',
    'six'
]

setup(
    name='coolname',
    version='0.1.0',
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
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    test_suite='tests',
    tests_require=test_requirements
)