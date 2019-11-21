#!/usr/bin/env python3

import datetime
import os
import sys
import yaml

from argparse import ArgumentParser


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

    data = data['ontologies']
    order = get_ontology_order(data)

    lines = []

    # bootstrap CSS
    lines.append('<link rel="stylesheet" href="{0}">'.format(bootstrap_css))

    # Custom CSS
    lines.append('<style>')
    lines.append('.tooltip-inner {')
    lines.append('  max-width: 280px;')
    lines.append('}')
    lines.append('')
    lines.append('.check {')
    lines.append('  text-align: center;')
    lines.append('}')
    lines.append('')
    lines.append('div.tableContainer {')
    lines.append('    clear: both;')
    lines.append('    height: 800px;')
    lines.append('    overflow: auto;')
    lines.append('}')
    lines.append('')
    lines.append('html>body div.tableContainer {')
    lines.append('    overflow: hidden;')
    lines.append('}')
    lines.append('')
    lines.append('div.tableContainer table {')
    lines.append('    float: left;')
    lines.append('}')
    lines.append('')
    lines.append('thead.fixedHeader tr {')
    lines.append('    position: relative;')
    lines.append('}')
    lines.append('')
    lines.append('html>body thead.fixedHeader tr {')
    lines.append('    display: block;')
    lines.append('}')
    lines.append('')
    lines.append('thead.fixedHeader th {')
    lines.append('    padding: 4px 3px;')
    lines.append('    text-align: left')
    lines.append('}')
    lines.append('')
    lines.append('thead.fixedHeader a, thead.fixedHeader a:link, \
        thead.fixedHeader a:visited {')
    lines.append('    display: block;')
    lines.append('    text-decoration: none;')
    lines.append('    width: 100%')
    lines.append('}')
    lines.append('')
    lines.append('html>body tbody.scrollContent {')
    lines.append('    display: block;')
    lines.append('    height: 640px;')
    lines.append('    overflow: auto;')
    lines.append('    width: 100%')
    lines.append('}')
    lines.append('')
    lines.append('.rotate {')
    lines.append('    transform: rotate(-45deg);')
    lines.append('    position: relative;')
    lines.append('    top: -30px;')
    lines.append('    left: -5px;')
    lines.append('    width: 100px !important;')
    lines.append('}')
    lines.append('')
    lines.append('html>body thead.fixedHeader th {')
    lines.append('    height: 85px !important;')
    lines.append('    max-width: 91px !important;')
    lines.append('    min-width: 91px !important;')
    lines.append('    overflow-wrap: break-word;')
    lines.append('    hyphens: auto;')
    lines.append('}')
    lines.append('')
    lines.append('html>body tbody.scrollContent td {')
    lines.append('    max-width: 91px !important;')
    lines.append('    min-width: 91px !important;')
    lines.append('    overflow-wrap: break-word;')
    lines.append('    hyphens: auto;')
    lines.append('}')
    lines.append('</style>')
    lines.append('<script src="{0}"></script>'.format(jquery))
    lines.append('<script src="{0}"></script>'.format(bootstrap_js))

    # Opening tags
    lines.append('<div class="row" style="padding-top: 20px;">')
    lines.append('  <div class="col-md-1"></div>')
    lines.append('  <div class="col-md-10">')

    # Page Headers
    date = datetime.datetime.today()
    lines.append('  <h1>OBO Foundry Dashboard [ALPHA]</h1>')
    lines.append('  <p class="lead">{0}</p>'.format(date.strftime('%Y-%m-%d')))
    lines.append('<div class="alert alert-info" role="alert">\
        <h4 class="alert-heading">The OBO Dashboard is a new feature under \
        active development.</h4> Our goal is to provide a set of automated \
        tests that establish a minimum level of compliance with OBO \
        Principles and best practises. Keep in mind that automated checks \
        often cannot capture the full intent of a given principle -- we do \
        our best while keeping the automated checks as fast and cheap as \
        possible.<br><br>\
        For each ontology, two aspects are checked: the OBO Registry entry, \
        and the latest release of the project\'s main OWL file. For each \
        check we provide links to the rule text and implementation.<br><br>\
        <p class="mb-0">Please give us your feedback! For general comments, please reply to \
        issue <a href=\
        "https://github.com/OBOFoundry/OBOFoundry.github.io/issues/1076" \
        target="_blank"><u>#1076</u></a>. For specific problems or bugs, \
        please <a href="\
        https://github.com/OBOFoundry/OBOFoundry.github.io/issues/new/choose" \
        target="_blank"><u>create a new issue.</u></a></p></div>')
    lines.append('  <p><center><small>Click on each ontology ID for a \
        detailed report.<br>')
    lines.append('  Click on a table header to find out more details about \
        the check.</small></center></p>')
    lines.append('    <table class="table table-bordered">')
    lines.append('      <thead class="fixedHeader">')
    lines.append('      <tr>')

    # Table Headers
    lines.append('        <th style="padding-bottom:30px;"><b>ID</b></th>')
    for principle, link in principle_map.items():
        lines.append('        <th><div class="rotate">\
            <b><a href="{0}">{1}</a></b></div></th>'.format(
                link, principle))
    lines.append('        <th><div class="rotate">\
        <b><a href="http://robot.obolibrary.org/report">ROBOT Report</a>\
        </b></div></th>')
    lines.append('        <th><div class="rotate"><b>Summary</b></div></th>')
    lines.append('      </tr>')
    lines.append('      </thead>')

    lines.append('      <tbody class="scrollContent">')
    for o in order:
        dashboard_yaml = '{0}/{1}/dashboard.yml'.format(dashboard_dir, o)
        if not os.path.exists(dashboard_yaml):
            continue
        with open(dashboard_yaml, 'r') as f:
            this_data = yaml.load(f, Loader=yaml.SafeLoader)

        summary = this_data['summary']
        results = this_data['results']

        lines.append('      <tr>')
        lines.append('        <td><b>\
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
                '        <td class="check {0}">{1}</td>'.format(
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
            '        <td class="check {0}">{1}</td>'.format(td_class, icon))
        lines.append('      </tr>')

    # closing tags
    lines.append('      </tbody>')
    lines.append('    </table>')
    lines.append('    </div>')
    lines.append('  </div>')
    lines.append('</div>')
    lines.append('<script>')
    lines.append('  $(function () {')
    lines.append('    $(\'[data-toggle="tooltip"]\').tooltip()')
    lines.append('  });')
    lines.append('</script>')

    html = '\n'.join(lines)
    with open(outfile, 'w+') as f:
        f.write(html)


def get_ontology_order(data):
    """
    """
    order = []
    for item in data:
        ont_id = item['id']
        order.append(ont_id)
    return order


# HTML style/JS links
jquery = 'http://ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.js'
bootstrap_css = 'https://stackpath.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css'
bootstrap_js = 'https://stackpath.bootstrapcdn.com/bootstrap/3.4.1/js/bootstrap.min.js'

# Pattern for icons with messages
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
                 "Docu-mented":
                 "{0}/principles/fp-008-documented.html".format(host),
                 "Users":
                 "{0}/principles/fp-009-users.html".format(host),
                 "Authority":
                 "{0}/principles/fp-011-locus-of-authority.html".format(host),
                 "Naming":
                 "{0}/principles/fp-012-naming-conventions.html".format(host),
                 "Maintained":
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

if __name__ == '__main__':
    main(sys.argv)
