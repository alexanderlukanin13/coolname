import argparse
import sys

from coolname import generate


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Generate slug to stdout')
    parser.add_argument('pattern', nargs='?', type=int, choices=[2, 3, 4], default=None)
    parser.add_argument('-s', '--separator', default='-')
    parser.add_argument('-n', '--number', type=int, default=1, help='how many slugs to generate (default: 1)')
    args = parser.parse_args(argv)
    if args.number < 1:
        parser.error('--number must be a positive integer')
    return args


def main() -> None:
    args = parse_args(sys.argv[1:])
    for _ in range(args.number):
        print(args.separator.join(generate(args.pattern)))


if __name__ == '__main__':
    main()  # pragma: nocover
