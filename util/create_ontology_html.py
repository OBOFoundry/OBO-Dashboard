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
                          autochecklinks=automated_map,
                          o=data)

    args.output.write(res)


check_order = ['FP01 Open',
               'FP02 Common Format',
               'FP03 URIs',
               'FP04 Versioning',
               'FP05 Scope',
               'FP06 Textual Definitions',
               'FP07 Relations',
               'FP08 Documented',
               'FP09 Plurality of Users',
               'FP11 Locus of Authority',
               'FP12 Naming Conventions',
               'FP16 Maintenance',
               'FP20 Responsiveness']

link_map = {
    'FP01': 'http://obofoundry.org/principles/fp-001-open.html',
    'FP02': 'http://obofoundry.org/principles/fp-002-format.html',
    'FP03': 'http://obofoundry.org/principles/fp-003-uris.html',
    'FP04': 'http://obofoundry.org/principles/fp-004-versioning.html',
    'FP05': 'http://obofoundry.org/principles/fp-005-delineated-content.html',
    'FP06': 'http://obofoundry.org/principles/fp-006-textual-definitions.html',
    'FP07': 'http://obofoundry.org/principles/fp-007-relations.html',
    'FP08': 'http://obofoundry.org/principles/fp-008-documented.html',
    'FP09': 'http://obofoundry.org/principles/fp-009-users.html',
    'FP11': 'http://obofoundry.org/principles/fp-011-locus-of-authority.html',
    'FP12': 'http://obofoundry.org/principles/fp-012-naming-conventions.html',
    'FP16': 'http://obofoundry.org/principles/fp-016-maintenance.html',
    'FP20': 'http://obofoundry.org/principles/fp-020-responsiveness.html'
}

automated_map = {
    'FP01': 'https://obofoundry.org/principles/checks/fp_001',
    'FP02': 'https://obofoundry.org/principles/checks/fp_002',
    'FP03': 'https://obofoundry.org/principles/checks/fp_003',
    'FP04': 'https://obofoundry.org/principles/checks/fp_004',
    'FP05': 'https://obofoundry.org/principles/checks/fp_005',
    'FP06': 'https://obofoundry.org/principles/checks/fp_006',
    'FP07': 'https://obofoundry.org/principles/checks/fp_007',
    'FP08': 'https://obofoundry.org/principles/checks/fp_008',
    'FP09': 'https://obofoundry.org/principles/checks/fp_009',
    'FP11': 'https://obofoundry.org/principles/checks/fp_011',
    'FP12': 'https://obofoundry.org/principles/checks/fp_012',
    'FP16': 'https://obofoundry.org/principles/checks/fp_016',
    'FP20': 'https://obofoundry.org/principles/checks/fp_020'
}

if __name__ == '__main__':
    main(sys.argv)
