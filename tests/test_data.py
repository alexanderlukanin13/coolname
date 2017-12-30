from unittest import TestCase

from coolname import RandomGenerator
from coolname.data import config
from coolname.impl import _unicode

class DataTest(TestCase):

    def test_initialization(self):
        generator = RandomGenerator(config)
        assert generator.generate_slug()

    def test_all_unicode(self):
        for name, rule in config.items():
            if rule['type'] == 'words':
                assert all(isinstance(x, _unicode) for x in rule['words'])
            elif rule['type'] == 'phrases':
                assert all(all(isinstance(y, _unicode) for y in x) for x in rule['phrases'])
            elif rule['type'] == 'const':
                assert isinstance(rule['value'], _unicode)
            elif rule['type'] in ('nested', 'cartesian'):
                pass
            else:
                raise AssertionError('Rule {!r} has unexpected type {!r}'.format(name, rule['type']))
