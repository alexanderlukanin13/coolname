from io import StringIO
import os
import tempfile

import unittest

import six

from coolname import InitializationError
from coolname.loader import _load_wordlist, _load_data

from .common import patch, TestCase


class LoaderTest(TestCase):

    def test_load_wordlist(self):
        s = StringIO(six.u('\n'.join([
            'alpha',
            '',  # blank line
            'beta',
            '# Some comment',
            'gamma',
        ])))
        wordlist = _load_wordlist('words', s)
        self.assertEqual(wordlist, ['alpha', 'beta', 'gamma'])

    def test_invalid_wordlist(self):
        s = StringIO(six.u('\n'.join([
            'alpha',
            'augmentation',  # line exceeds 11 characters
        ])))
        with self.assertRaisesRegex(InitializationError, r"Invalid syntax at wordlist 'words' line 2: u?'augmentation'"):
            _load_wordlist('words', s)

    def test_load_data_no_dir(self):
        path = os.path.join(tempfile.gettempdir(), 'does', 'not', 'exist')
        with self.assertRaisesRegex(InitializationError, 'Directory not found: {}'.format(path)):
            _load_data(path)

    @patch('json.load')
    @patch('coolname.loader._load_wordlist')
    @patch('codecs.open')
    @patch('os.path.isdir')
    @patch('os.listdir')
    def test_load_data(self,
                       listdir_mock, isdir_mock, open_mock,
                       load_wordlist_mock, json_mock):
        listdir_mock.return_value = ['one.txt', 'two.txt']
        isdir_mock.return_value = True
        lists = iter([['one', 'ichi'], ['two', 'ni']])
        load_wordlist_mock.side_effect = lambda x, y: next(lists)
        json_mock.return_value = {'hello': 'world'}
        path = '/data'
        config, wordlists = _load_data(path)
        self.assertEqual(config, {'hello': 'world'})
        self.assertEqual(wordlists, {
            'one': ['one', 'ichi'],
            'two': ['two', 'ni'],
        })

    @patch('codecs.open', side_effect=OSError('BOOM!'))
    @patch('os.path.isdir', return_value=True)
    @patch('os.listdir', return_value=['one.txt', 'two.txt'])
    def test_load_data_os_error(self, listdir_mock, isdir_mock, open_mock):
        with self.assertRaisesRegex(InitializationError,
                                    r'Failed to read /data/one.txt: BOOM!'):
            _load_data('/data')

    @patch('codecs.open')
    @patch('os.path.isdir', return_value=True)
    @patch('os.listdir', return_value=['one.txt'])
    def test_load_data_failed_to_read_config(self, listdir_mock, isdir_mock,
                                             open_mock):
        # First call to open() should pass,
        # second call should raise OSError.
        class open_then_fail(object):

            def __init__(self):
                self.called = False

            def __call__(self, *x, **y):
                if self.called:
                    raise OSError('BOOM!')
                self.called = True
                return StringIO(six.u('word'))

        open_mock.side_effect = open_then_fail()
        with self.assertRaisesRegex(InitializationError,
                                    "Failed to read config from "
                                    "/data/config.json: BOOM!"):
            _load_data('/data')

    @patch('codecs.open', side_effect=lambda *x, **y: StringIO(six.u('word')))
    @patch('os.path.isdir', return_value=True)
    @patch('os.listdir', return_value=['one.txt', 'two.txt'])
    def test_load_data_invalid_json(self, *args):
        with self.assertRaisesRegex(InitializationError,
                                    r"Invalid config: Invalid JSON: "
                                    r"(Expecting value: line 1 column 1 \(char 0\)|"
                                    r"No JSON object could be decoded)"):
            _load_data('/data')


if __name__ == '__main__':
    import sys
    sys.exit(unittest.main())
