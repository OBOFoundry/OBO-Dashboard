#!/usr/bin/env python3

from pathlib import Path
import datetime
import os
import sys
import yaml

from argparse import ArgumentParser
from jinja2 import Template
from lib import DashboardConfig, count_up, save_yaml, save_json, round_float, compute_dashboard_score, compute_obo_score


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
    parser.add_argument('dashboard_config',
                        type=str,
                        help='Dashboard config file (typically dashboard-config.yml)')
    parser.add_argument('dashboard_score_data',
                        type=str,
                        help='Dashboard yaml file with results')
    parser.add_argument('robot_version',
                        type=str,
                        help='Version of ROBOT used to build dashboard (version number)')
    parser.add_argument('obomd_version',
                        type=str,
                        help='Version of OBO Metadata used to build dashboard (URL)')
    parser.add_argument('outfile',
                        type=str,
                        help='Output dashboard HTML file')
    args = parser.parse_args()

    registry_yaml = args.registry_yaml
    dashboard_dir = args.dashboard_dir
    dashboard_score_data_file = args.dashboard_score_data
    outfile = args.outfile
    dashboard_config = args.dashboard_config

    config = DashboardConfig(dashboard_config)

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

    ontologies = reorder_status(ontologies)

    # Load Jinja2 template
    template = Template(open('util/templates/index.html.jinja2').read())

    # Generate the HTML output
    date = datetime.datetime.today()
    res = template.render(checkorder=check_order,
                          date=date.strftime('%Y-%m-%d'),
                          robot=args.robot_version,
                          obomd=args.obomd_version,
                          ontologies=ontologies,
                          title=config.get_title(),
                          description=config.get_description()
                          )

    with open(outfile, 'w+') as f:
        f.write(res)

    oboscore_weights = config.get_oboscore_weights()
    oboscore_maximpacts = config.get_oboscore_max_impact()
    dashboard_score_data = dict()
    dashboard_score_data['ontologies'] = ontologies
    dashboard_score_data['oboscore'] = {}
    dashboard_score_data['oboscore']['dashboard_score_weights'] = oboscore_weights
    dashboard_score_data['oboscore']['dashboard_score_max_impact'] = oboscore_maximpacts
    save_yaml(dashboard_score_data, dashboard_score_data_file)
    dashboard_score_data_json_file = Path(dashboard_score_data_file).parent / f"{dashboard_score_data_file.stem}.json"
    save_json(dashboard_score_data, dashboard_score_data_json_file)


def get_ontology_order(data):
    """
    """
    order = []
    for item in data:
        ont_id = data[item]['id']
        order.append(ont_id)
    return order


def reorder_status(data):
    """
    """
    ORDERING = {"ERROR": 1, "WARN": 0, "INFO": 0, "PASS": 0}
    return sorted(
        data,
        key=lambda ont: ORDERING[ont['summary']['status']] if 'summary' in ont else 2
    )


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
               'FP20 Responsiveness',
               'ROBOT Report']

if __name__ == '__main__':
    main(sys.argv)
