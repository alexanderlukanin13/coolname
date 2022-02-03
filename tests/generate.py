import argparse
import os
import sys
import time

PROJECT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_PATH not in sys.path:
    sys.path.append(PROJECT_PATH)

from coolname import generate_slug


def main(argv):
    if sys.version_info[:2] < (3, 6):
        sys.stderr.write('This script requires Python 3.6+\n')
        return 1
    parser = argparse.ArgumentParser(description='Generate slug to stdout')
    parser.add_argument('length', default=None, nargs='?', type=int, help='Number of words')
    parser.add_argument('-w', '--word', help='With particular substring')
    parser.add_argument('-a', '--attempts', type=int, default=100000, help='Number of attempts before giving up')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output (with timing)')
    args = parser.parse_args(argv)
    generate_slug(args.length)  # for more precise timing
    if args.word:
        words = args.word.split(',')
        slug = None
        for i in range(0, args.attempts):
            start_time = time.perf_counter()
            s = generate_slug(args.length)
            elapsed_time = time.perf_counter() - start_time
            if any(x in s for x in words):
                slug = s
                break
        if slug is None:
            print('Failed to generate in {} attempts'.format(args.attempts))
            return 1
    else:
        start_time = time.perf_counter()
        slug = generate_slug(args.length)
        elapsed_time = time.perf_counter() - start_time
    print(slug)
    if args.verbose:
        sys.stderr.write('Generated in {:0.06f} seconds\n'.format(elapsed_time))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
