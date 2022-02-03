import argparse
import itertools
import sys


class NotRandom(object):

    def __init__(self):
        self.gen = itertools.count()

    def randrange(self, r):
        return next(self.gen) % r


def _parse_args(argv):
    parser = argparse.ArgumentParser(description='Auxiliary script to run coolname in a separate process.')
    parser.add_argument('number_of_slugs', type=int, help='Number of slugs to generate')
    return parser.parse_args(argv)


def main(argv):
    args = _parse_args(argv)
    import coolname
    coolname.replace_random(NotRandom())
    for i in range(args.number_of_slugs):
        print(coolname.generate_slug())


if __name__ == '__main__':
    main(sys.argv[1:])
