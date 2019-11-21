#!/usr/bin/env python3

import json
import os
import re
import sys

from argparse import ArgumentParser


def main(args):
    """
    """
    parser = ArgumentParser(description='Create a report HTML page')
    parser.add_argument('report',
                        type=str,
                        help='TSV report to generate HTML')
    parser.add_argument('title',
                        type=str,
                        help='HTML page title')
    parser.add_argument('context',
                        type=str,
                        help='Ontology prefixes')
    parser.add_argument('outfile',
                        type=str,
                        help='Output report HTML file')
    args = parser.parse_args()

    report_file = args.report

    if not os.path.exists(report_file):
        sys.exit(1)

    title = args.title
    context_file = args.context
    outfile = args.outfile

    context = load_context(context_file)

    headers = []
    lines = []
    with open(report_file, 'r') as f:
        headers = next(f).split('\t')
        for s in f:
            line = s.split('\t')
            lines.append(line)

    html = []

    html.append('<head>')
    html.append('  <link rel="stylesheet" href=\
"https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css">')
    html.append('</head>')
    html.append('<body>')
    html.append('<div class="container">')
    html.append('<div class="row">')
    html.append('<div class="col-md-1"></div>')
    html.append('<div class="col-md-10">')
    html.append('<h1>{0}</h1>'.format(title))
    html.append('<p><center><small>Click on the Rule Name for details on how \
        to fix.<br>Click on any term to direct to the term page\
        </small></center></p>')

    # Table headers
    html.append('<table class="table">')
    html.append('  <tr>')
    html.append('    <th><b>Row</b></th>')
    for h in headers:
        html.append('    <th><b>{0}</b></th>'.format(h))
    html.append('  </tr>')

    # Table contents
    line_num = 0
    for line in lines:
        line_num += 1
        status = line[0]
        if status in class_map:
            td_class = class_map[status]
        else:
            td_class = 'table-active'
        html.append('  <tr class="{0}">'.format(td_class))
        html.append('    <td>{0}</td>'.format(line_num))
        for cell in line:
            if cell in report_doc_map:
                link = report_doc_map[cell]
                cell = '<a href="{0}" target="_blank">{1}</a>'.format(
                    link, cell)
            html.append('    <td>{0}</td>'.format(
                maybe_get_link(cell, context)))
        html.append('  </tr>')
    html.append('</table>')
    html.append('</div>')
    html.append('</div>')
    html.append('</div>')

    with open(outfile, 'w+') as f:
        f.write('\n'.join(html))


def load_context(context_file):
    """
    """
    with open(context_file) as f:
        data = json.load(f)
    return data['@context']


def maybe_get_link(cell, context):
    """
    """
    s = re.search(r'^.+ \[(.+)\]$', cell)
    iri = None
    if s:
        curie_or_iri = s.group(1)
        curie = re.search(r'([A-Za-z0-9]+):([A-Za-z0-9-]+)', curie_or_iri)
        if curie:
            # This is a CURIE
            prefix = curie.group(1)
            local_id = curie.group(2)
            if prefix in context:
                namespace = context[prefix]
                iri = namespace + local_id
        else:
            s = re.search(r'^(http|https|ftp)://.*$', curie_or_iri)
            if s:
                # This is a link
                iri = curie_or_iri
    if iri:
        return '<a href="{0}" target="_blank">{1}</a>'.format(iri, cell)
    return cell


# CSS classes for each level
class_map = {
    'PASS': 'table-success',
    'INFO': 'table-info',
    'WARN': 'table-warning',
    'ERROR': 'table-danger'
}


report_doc_map = {
    'annotation_whitespace':
        'http://robot.obolibrary.org/report_queries/annotation_whitespace',
    'deprecated_boolean_datatype':
        'http://robot.obolibrary.org/report_queries/deprecated_boolean_datatype',
    'deprecated_class_reference':
        'http://robot.obolibrary.org/report_queries/deprecated_class_reference',
    'deprecated_property_reference':
        'http://robot.obolibrary.org/report_queries/deprecated_property_reference',
    'duplicate_definition':
        'http://robot.obolibrary.org/report_queries/duplicate_definition',
    'duplicate_exact_synonym':
        'http://robot.obolibrary.org/report_queries/duplicate_exact_synonym',
    'duplicate_label_synonym':
        'http://robot.obolibrary.org/report_queries/duplicate_label_synonym',
    'duplicate_label':
        'http://robot.obolibrary.org/report_queries/duplicate_label',
    'duplicate_scoped_synonym':
        'http://robot.obolibrary.org/report_queries/duplicate_scoped_synonym',
    'equivalent_pair':
        'http://robot.obolibrary.org/report_queries/equivalent_pair',
    'invalid_xref':
        'http://robot.obolibrary.org/report_queries/invalid_xref',
    'label_formatting':
        'http://robot.obolibrary.org/report_queries/label_formatting',
    'label_whitespace':
        'http://robot.obolibrary.org/report_queries/label_whitespace',
    'lowercase_definition':
        'http://robot.obolibrary.org/report_queries/lowercase_definition',
    'missing_definition':
        'http://robot.obolibrary.org/report_queries/missing_definition',
    'missing_label':
        'http://robot.obolibrary.org/report_queries/missing_label',
    'missing_obsolete_label':
        'http://robot.obolibrary.org/report_queries/missing_obsolete_label',
    'missing_ontology_description':
        'http://robot.obolibrary.org/report_queries/missing_ontology_description',
    'missing_ontology_license':
        'http://robot.obolibrary.org/report_queries/missing_ontology_license',
    'missing_ontology_title':
        'http://robot.obolibrary.org/report_queries/missing_ontology_title',
    'missing_superclass':
        'http://robot.obolibrary.org/report_queries/missing_superclass',
    'misused_obsolete_label':
        'http://robot.obolibrary.org/report_queries/misused_obsolete_label',
    'multiple_definitions':
        'http://robot.obolibrary.org/report_queries/multiple_definitions',
    'multiple_equivalent_classes':
        'http://robot.obolibrary.org/report_queries/multiple_equivalent_classes',
    'multiple_labels':
        'http://robot.obolibrary.org/report_queries/multiple_labels',
}


if __name__ == '__main__':
    main(sys.argv)
