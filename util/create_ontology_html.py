#!/usr/bin/env python3

import os
import sys
import yaml

from argparse import ArgumentParser, FileType
from jinja2 import Template


def main(args):
    """
    """
    parser = ArgumentParser(description='Create a HTML report page')
    parser.add_argument('yaml',
                        type=FileType('r'),
                        help='Dashboard YAML file')
    parser.add_argument('template',
                        type=FileType('r'),
                        help='Template file')
    parser.add_argument('output',
                        type=FileType('w'),
                        help='Output HTML file')
    args = parser.parse_args()

    # get the data from the dashboard
    data = yaml.load(args.yaml, Loader=yaml.SafeLoader)

    # Load Jinja2 template
    template = Template(args.template.read())

    # Generate the HTML output
    res = template.render(checkorder=check_order,
                          checklinks=link_map,
                          o=data)

    args.output.write(res)


check_order = ['FP1 Open',
               'FP2 Common Format',
               'FP3 URIs',
               'FP4 Versioning',
               'FP5 Scope',
               'FP6 Textual Definitions',
               'FP7 Relations',
               'FP8 Documented',
               'FP9 Plurality of Users',
               'FP11 Locus of Authority',
               'FP12 Naming Conventions',
               'FP16 Maintenance',
               'ROBOT Report']

link_map = {
    'FP1': 'http://obofoundry.org/principles/checks/fp_001',
    'FP2': 'http://obofoundry.org/principles/checks/fp_002',
    'FP3': 'http://obofoundry.org/principles/checks/fp_003',
    'FP4': 'http://obofoundry.org/principles/checks/fp_004',
    'FP5': 'http://obofoundry.org/principles/checks/fp_005',
    'FP6': 'http://obofoundry.org/principles/checks/fp_006',
    'FP7': 'http://obofoundry.org/principles/checks/fp_007',
    'FP8': 'http://obofoundry.org/principles/checks/fp_008',
    'FP9': 'http://obofoundry.org/principles/checks/fp_009',
    'FP11': 'http://obofoundry.org/principles/checks/fp_011',
    'FP12': 'http://obofoundry.org/principles/checks/fp_012',
    'FP16': 'http://obofoundry.org/principles/checks/fp_016',
    'ROBOT Report': 'http://robot.obolibrary.org/report'
}

if __name__ == '__main__':
    main(sys.argv)
