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
    'FP1': 'http://obofoundry.org/principles/fp-001-open.html',
    'FP2': 'http://obofoundry.org/principles/fp-002-format.html',
    'FP3': 'http://obofoundry.org/principles/fp-003-uris.html',
    'FP4': 'http://obofoundry.org/principles/fp-004-versioning.html',
    'FP5': 'http://obofoundry.org/principles/fp-005-delineated-content.html',
    'FP6': 'http://obofoundry.org/principles/fp-006-textual-definitions.html',
    'FP7': 'http://obofoundry.org/principles/fp-007-relations.html',
    'FP8': 'http://obofoundry.org/principles/fp-008-documented.html',
    'FP9': 'http://obofoundry.org/principles/fp-009-users.html',
    'FP11': 'http://obofoundry.org/principles/fp-011-locus-of-authority.html',
    'FP12': 'http://obofoundry.org/principles/fp-012-naming-conventions.html',
    'FP16': 'http://obofoundry.org/principles/fp-016-maintenance.html',
    'ROBOT Report': 'http://robot.obolibrary.org/report'
}

if __name__ == '__main__':
    main(sys.argv)
