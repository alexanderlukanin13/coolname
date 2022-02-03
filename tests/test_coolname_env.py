"""
This module contains tests for COOLNAME_DATA_DIR and COOLNAME_DATA_MODULE.
"""
import os
import os.path as op
import subprocess
import sys

from .common import PROJECT_DIR, EXAMPLES_DIR


RUSSIAN = [
    'белая-корова',
    'белая-кошка',
    'белая-собака',
    'чёрная-корова',
    'чёрная-кошка',
    'чёрная-собака'
]
# In module, there are only 4 combinations
RUSSIAN_M = [
    'белая-кошка',
    'белая-собака',
    'чёрная-кошка',
    'чёрная-собака',
    'белая-кошка',
    'белая-собака'
]


def generate_slugs(number_of_slugs, data_dir=None, data_module=None, path=None, expect_returncode=0):
    env = dict(os.environ)
    env['PYTHONPATH'] = PROJECT_DIR
    if path:
        env['PYTHONPATH'] += os.pathsep + path
    if data_dir:
        env['COOLNAME_DATA_DIR'] = data_dir
    if data_module:
        env['COOLNAME_DATA_MODULE'] = data_module
    process = subprocess.Popen([sys.executable, 'tests/import_coolname_and_print_slugs.py', str(number_of_slugs)],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               cwd=PROJECT_DIR, env=env)
    process.wait()
    assert process.returncode == expect_returncode
    output = process.stdout.read().decode('utf8')
    if not output:
        output = process.stderr.read().decode('utf8')
    return [x.strip() for x in output.split('\n') if x.strip()]


def test_coolname_env():
    # Only COOLNAME_DATA_DIR
    assert generate_slugs(len(RUSSIAN), data_dir=op.join(EXAMPLES_DIR, 'russian')) == RUSSIAN
    # Only COOLNAME_DATA_MODULE
    assert generate_slugs(len(RUSSIAN_M), data_module='russian_module', path=EXAMPLES_DIR) == RUSSIAN_M
    # Both: data dir has more priority than the module
    assert generate_slugs(len(RUSSIAN),
                          data_dir=op.join(EXAMPLES_DIR, 'russian'),
                          data_module='russian_module',
                          path=EXAMPLES_DIR) == RUSSIAN
    # Both, but data dir does not exist - fall back to module
    assert generate_slugs(len(RUSSIAN_M),
                          data_dir=op.join(EXAMPLES_DIR, 'no_such'),
                          data_module='russian_module',
                          path=EXAMPLES_DIR) == RUSSIAN_M
    # Only COOLNAME_DATA_DIR, and it is invalid
    lines = generate_slugs(1, data_dir='no_such', expect_returncode=1)
    assert lines[-1] == 'ImportError: Configure valid COOLNAME_DATA_DIR and/or COOLNAME_DATA_MODULE'
