#!/bin/env/python
import os
from subprocess import call


if __name__ == '__main__':
    if 'TRAVIS' in os.environ:
        raise SystemExit(call('coveralls'))
