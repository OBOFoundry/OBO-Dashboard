#!/usr/bin/env python3

import datetime
import os
import sys
import yaml

from argparse import ArgumentParser
from jinja2 import Template
from lib import DashboardConfig, count_up, save_yaml


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
    oboscore_weights = config.get_oboscore_weights()
    oboscore_maximpacts = config.get_oboscore_max_impact()
    ontologies = []
    for o in order:
        dashboard_yaml = '{0}/{1}/dashboard.yml'.format(dashboard_dir, o)
        if not os.path.exists(dashboard_yaml):
            continue
        this_data = dict()
        with open(dashboard_yaml, 'r') as f:
            this_data = yaml.load(f, Loader=yaml.SafeLoader)
            this_data['oboscore'] = compute_obo_score(this_data, oboscore_weights, oboscore_maximpacts)
        this_data['mirror_from'] = data[o]['mirror_from']
        this_data['base_generated'] = "-base" not in this_data['mirror_from']
        ontologies.append(this_data)

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

    dashboard_score_data = dict()
    dashboard_score_data['ontologies'] = ontologies
    dashboard_score_data['oboscore_weights'] = oboscore_weights
    save_yaml(dashboard_score_data, dashboard_score_data_file)


def get_ontology_order(data):
    """
    """
    order = []
    for item in data:
        ont_id = data[item]['id']
        order.append(ont_id)
    return order


def compute_obo_score(data, weights, maximpacts):

    if 'failure' in data:
        return 0

    oboscore = 100
    no_base = 0
    report_errors = 0
    report_warning = 0
    report_info = 0

    overall_error = 0
    overall_warning = 0
    overall_info = 0

    report_errors_max = 0
    report_warning_max = 0
    report_info_max = 0

    overall_error_max = 0
    overall_warning_max = 0
    overall_info_max = 0

    if 'base_generated' in data and data['base_generated'] == True:
        no_base = weights['base_generated']

    if 'results' in data:
        if 'ROBOT Report' in data['results']:
            if 'results' in data['results']['ROBOT Report']:
                report_errors = data['results']['ROBOT Report']['results']['ERROR']
                report_warning = data['results']['ROBOT Report']['results']['WARN']
                report_info = data['results']['ROBOT Report']['results']['INFO']

    if 'summary' in data:
        overall_error = data['summary']['summary_count']['ERROR']
        overall_warning = data['summary']['summary_count']['WARN']
        overall_info = data['summary']['summary_count']['INFO']

    oboscore = oboscore - score_max(weights['no_base'] * no_base, maximpacts['no_base'])
    oboscore = oboscore - score_max(weights['overall_error'] * overall_error, maximpacts['overall_error'])
    oboscore = oboscore - score_max(weights['overall_warning'] * overall_warning, maximpacts['overall_warning'])
    oboscore = oboscore - score_max(weights['overall_info'] * overall_info, maximpacts['overall_info'])
    oboscore = oboscore - score_max(weights['report_errors'] * report_errors, maximpacts['report_errors'])
    oboscore = oboscore - score_max(weights['report_warning'] * report_warning, maximpacts['report_warning'])
    oboscore = oboscore - score_max(weights['report_info'] * report_info, maximpacts['report_info'])
    return "%.2f" % oboscore


def score_max(score,maxscore):
    if score > maxscore:
        return maxscore
    else:
        return score


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
               'ROBOT Report']

if __name__ == '__main__':
    main(sys.argv)
