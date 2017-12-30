# Pre-import a lot of standard library stuff
# to get accurate measurement of coolname memory consumption.
import argparse
import hashlib
import itertools
import json
import os
import random
import re
import sys
import time
from timeit import timeit


if __name__ == '__main__':
    argument_parser = argparse.ArgumentParser(
        description='Measure performance of coolname functions')
    argument_parser.add_argument('--dump', action='store_true', help='Dump whole tree')
    argument_parser.add_argument('--all',
                                 action='store_true',
                                 help='Measure repeat probability')
    arguments = argument_parser.parse_args(sys.argv[1:])

    # Make sure coolname is importable
    project_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
    if project_path not in sys.path:
        sys.path.append(project_path)

    # Use psutil to measure memory.
    try:
        import psutil
    except ImportError:
        print('Please install psutil')
        sys.exit(1)
    process = psutil.Process()
    rss_base = process.memory_info().rss
    vm_base = process.memory_info().vms

    # Import coolname and measure memory growth.
    # Give OS some time to correctly register amount of memory allocated.
    start_time = time.time()
    from coolname import generate, generate_slug, get_combinations_count
    print('Loading time:         {:.3f}'.format(time.time() - start_time))
    time.sleep(3)
    print('RSS growth:           {} K'.format((process.memory_info().rss - rss_base) // 1024))
    print('VM growth:            {} K'.format((process.memory_info().vms - vm_base) // 1024))

    # Measure average call time
    number = 100000
    print('generate() time:      {:.6f}'.format(timeit(generate, number=number) / number))
    print('generate_slug() time: {:.6f}'.format(timeit(generate_slug, number=number) / number))

    # Total combinations count
    print('Total combinations:   {:,}'.format(get_combinations_count()))
    print('Combinations(4):      {:,}'.format(get_combinations_count(4)))
    print('Combinations(3):      {:,}'.format(get_combinations_count(3)))
    print('Combinations(2):      {:,}'.format(get_combinations_count(2)))

    # Check probability of repeat if we have used 0.1% of total namespace.
    # It should be around 0.0001.
    if arguments.all:
        combinations = get_combinations_count()
        items = set({})
        items_count = combinations // 10000
        while len(items) < items_count:
            items.add(generate_slug())
        repeats = 0
        loops = 100000
        for i in range(loops):
            if generate_slug() in items:
                repeats += 1
        print('Repeat probability:   {:.6f} (with {} names used)'.format(repeats / loops, len(items)))

    # Dump tree
    if arguments.dump:
        print()
        import coolname.impl
        print(coolname.impl._default._dump(sys.stdout, object_ids=True))