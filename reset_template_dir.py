#!/usr/bin/env python3
import sys

from run_common import reset_template_dir


def _print_how_to():
    print('please input path')
    print('(sample)')
    print('\t./reset_template_dir.py config_git_url template_dir_name phase')


if __name__ == "__main__":

    git_url = sys.argv[1]
    template_name = sys.argv[2]
    phase = sys.argv[3]

    if len(sys.argv) != 4:
        _print_how_to()
        exit(1)

    reset_template_dir(git_url, template_name, phase)
