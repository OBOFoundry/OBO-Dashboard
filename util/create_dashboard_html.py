#!/usr/bin/env python3

import datetime
import os
import sys
import yaml

from argparse import ArgumentParser
from jinja2 import Template


def main(args):
    """
    """
    parser = ArgumentParser(description='Create a dashboard HTML page')
    parser.add_argument('dashboard_dir',
                        type=str,
                        help='Directory of reports (<dir>/*/dashboard.yml)')
    parser.add_argument('registry_yaml',
                        type=str,
                        help='Ontology registry data')
    parser.add_argument('outfile',
                        type=str,
                        help='Output dashboard HTML file')
    args = parser.parse_args()

    registry_yaml = args.registry_yaml
    dashboard_dir = args.dashboard_dir
    outfile = args.outfile

    with open(registry_yaml, 'r') as f:
        data = yaml.load(f, Loader=yaml.SafeLoader)

    # Put ontology data in order
    data = data['ontologies']
    order = get_ontology_order(data)
    ontologies = []
    for o in order:
        dashboard_yaml = '{0}/{1}/dashboard.yml'.format(dashboard_dir, o)
        if not os.path.exists(dashboard_yaml):
            continue
        with open(dashboard_yaml, 'r') as f:
            this_data = yaml.load(f, Loader=yaml.SafeLoader)

        ontologies.append(this_data)

    # Load Jinja2 template
    template = Template(open('util/templates/index.html.jinja2').read())

    # Generate the HTML output
    date = datetime.datetime.today()
    res = template.render(checkorder=check_order,
                          date=date.strftime('%Y-%m-%d'),
                          ontologies=ontologies)

    with open(outfile, 'w+') as f:
        f.write(res)


def get_ontology_order(data):
    """
    """
    order = []
    for item in data:
        ont_id = item['id']
        order.append(ont_id)
    return order


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

if __name__ == '__main__':
    main(sys.argv)
