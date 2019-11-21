#!/usr/bin/env python3

import os
import sys
import yaml

from argparse import ArgumentParser

jquery = 'http://ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.js'
bootstrap_css = 'https://stackpath.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css'
bootstrap_js = 'https://stackpath.bootstrapcdn.com/bootstrap/3.4.1/js/bootstrap.min.js'

icon_pat = '<img src="assets/{0}.svg"\
 height="15px"\
 data-toggle="tooltip"\
 data-html="true"\
 data-placement="right"\
 title="{1}">'

# Map of principle names to links for Dashboard
host = 'http://obofoundry.org/'
principle_map = {"Open":
                 "{0}/principles/fp-001-open.html".format(host),
                 "Format":
                 "{0}/principles/fp-002-format.html".format(host),
                 "URIs":
                 "{0}/principles/fp-003-uris.html".format(host),
                 "Versioning":
                 "{0}/principles/fp-004-versioning.html".format(host),
                 "Scope":
                 "{0}/principles/fp-005-delineated-content.html".format(host),
                 "Definitions":
                 "{0}/principles/fp-006-textual-definitions.html".format(host),
                 "Relations":
                 "{0}/principles/fp-007-relations.html".format(host),
                 "Documentation":
                 "{0}/principles/fp-008-documented.html".format(host),
                 "Users":
                 "{0}/principles/fp-009-users.html".format(host),
                 "Authority":
                 "{0}/principles/fp-011-locus-of-authority.html".format(host),
                 "Naming":
                 "{0}/principles/fp-012-naming-conventions.html".format(host),
                 "Maintenance":
                 "{0}/principles/fp-016-maintenance.html".format(host)}

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


def main(args):
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

    data = data['ontologies']
    order = get_ontology_order(data)

    lines = []

    # bootstrap CSS
    lines.append('<link rel="stylesheet" href="{0}">'.format(bootstrap_css))
    lines.append('<style>')
    lines.append('.tooltip-inner {')
    lines.append('\tmax-width: 280px;')
    lines.append('}')
    lines.append('.check {')
    lines.append('\ttext-align: center;')
    lines.append('}')
    lines.append('</style>')
    lines.append('<script src="{0}"></script>'.format(jquery))
    lines.append('<script src="{0}"></script>'.format(bootstrap_js))

    # Opening tags
    lines.append('<div class="row" style="padding-top: 20px;">')
    lines.append('\t<div class="col-md-1"></div>')
    lines.append('\t<div class="col-md-10">')
    lines.append('\t\t<table class="table table-bordered">')
    lines.append('\t\t\t<tr>')

    # Headers
    lines.append('\t\t\t\t<th><b>ID</b></th>')
    for principle, link in principle_map.items():
        lines.append(
            '\t\t\t\t<th><b><a href="{0}">{1}</a></b></th>'.format(
                link, principle))
    lines.append('\t\t\t\t<th><b><a href="">ROBOT Report</a></b></th>')
    lines.append('\t\t\t\t<th><b>Summary</b></th>')
    lines.append('\t\t\t</tr>')

    for o in order:
        dashboard_yaml = '{0}/{1}/dashboard.yml'.format(dashboard_dir, o)
        if not os.path.exists(dashboard_yaml):
            continue
        with open(dashboard_yaml, 'r') as f:
            this_data = yaml.load(f, Loader=yaml.SafeLoader)

        summary = this_data['summary']
        results = this_data['results']

        lines.append('\t\t\t<tr>')
        lines.append('\t\t\t\t<td><b>\
<a href="{0}/dashboard.html">{0}</a></b></td>'.format(o))
        for check in check_order:
            if check in results:
                details = results[check]
                if 'status' in details:
                    status = details['status']
                else:
                    status = ''
                if 'comment' in details:
                    comment = details['comment']
                else:
                    comment = None
            else:
                status = ''

            if status == 'PASS':
                td_class = 'success'
                icon = '<img src="assets/check.svg" height="15px">'

            elif status == 'INFO':
                td_class = 'info'
                if comment:
                    icon = icon_pat.format('info', comment)
                else:
                    icon = '<img src="assets/info.svg" height="15px">'

            elif status == 'WARN':
                td_class = 'warning'
                if comment:
                    icon = icon_pat.format('warning', comment)
                else:
                    icon = '<img src="assets/warning.svg" height="15px">'

            elif status == 'ERROR':
                td_class = 'danger'
                if comment:
                    icon = icon_pat.format('x', comment)
                else:
                    icon = '<img src="assets/x.svg" height="15px">'

            else:
                td_class = 'active'
                icon = None

            lines.append(
                '\t\t\t\t<td class="check {0}">{1}</td>'.format(
                    td_class, icon))

        # Get icon for summary
        summary_status = summary['status']

        if summary_status == 'PASS':
            td_class = 'success'
            icon = '<img src="assets/check.svg" height="15px">'

        elif summary_status == 'INFO':
            td_class = 'info'
            icon = '<img src="assets/info.svg" height="15px">'

        elif summary_status == 'WARN':
            td_class = 'warning'
            icon = '<img src="assets/warning.svg" height="15px">'

        elif summary_status == 'ERROR':
            td_class = 'danger'
            icon = '<img src="assets/x.svg" height="15px">'

        lines.append(
            '\t\t\t\t<td class="check {0}">{1}</td>'.format(td_class, icon))
        lines.append('\t\t\t</tr>')

    # closing tags
    lines.append('\t\t</table>')
    lines.append('\t</div>')
    lines.append('</div>')
    lines.append('<script>')
    lines.append('\t$(function () {')
    lines.append('\t\t$(\'[data-toggle="tooltip"]\').tooltip()')
    lines.append('\t});')
    lines.append('</script>')

    html = '\n'.join(lines)
    with open(outfile, 'w+') as f:
        f.write(html)


def get_ontology_order(data):
    order = []
    for item in data:
        ont_id = item['id']
        order.append(ont_id)
    return order


if __name__ == '__main__':
    main(sys.argv)
