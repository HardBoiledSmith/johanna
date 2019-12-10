#!/usr/bin/env python3
import sys

from run_common import reset_template_dir


def _print_how_to():
    print('please input path')
    print('(sample)')
    print('\t./generate_config.py dv-variable.json')


if __name__ == "__main__":

    git_url = sys.argv[1]
    template_name = sys.argv[2]
    phase = sys.argv[3]

    reset_template_dir(git_url, template_name, phase)
