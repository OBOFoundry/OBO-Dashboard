#!/usr/bin/env python3

import json
import os
import re
import sys

from argparse import ArgumentParser
from jinja2 import Template


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
    rows = []
    with open(report_file, 'r') as f:
        headers = next(f).split('\t')
        for s in f:
            row = s.split('\t')
            rows.append(row)

    contents = {'headers': headers, 'rows': rows}

    # Load Jinja2 template
    template = Template(open('util/templates/report.html.jinja2').read())

    # Generate the HTML output
    res = template.render(contents=contents,
                          maybe_get_link=maybe_get_link,
                          context=context,
                          title=title,
                          file=report_file.split('/')[-1:][0])

    with open(outfile, 'w+') as f:
        f.write(res)


def load_context(context_file):
    """
    """
    with open(context_file) as f:
        data = json.load(f)
    return data['@context']


def maybe_get_link(cell, context):
    """
    """
    url = None
    if cell in report_doc_map.keys():
        # First check if it is a ROBOT report link
        url = report_doc_map[cell]
    else:
        # Otherwise try to parse as CURIE or IRI
        curie = re.search(r'([A-Za-z0-9]+):([A-Za-z0-9-]+)', cell)
        if curie:
            # This is a CURIE
            prefix = curie.group(1)
            local_id = curie.group(2)
            if prefix in context:
                namespace = context[prefix]
                url = namespace + local_id
            elif prefix in other_prefixes:
                namespace = other_prefixes[prefix]
                url = namespace + local_id
        # IRIs might be in angle brackets
        iri = re.search(r'((http|https|ftp)://[^ <>]+)', cell)
        if iri:
            url = iri.group(1)
    if url:
        return '<a href="{0}">{1}</a>'.format(url, cell)
    return cell


# CSS classes for each level
class_map = {
    'PASS': 'table-success',
    'INFO': 'table-info',
    'WARN': 'table-warning',
    'ERROR': 'table-danger'
}

other_prefixes = {
    'dc': 'http://purl.org/dc/terms/',
    'dcterms': 'http://purl.org/dc/terms/',
    'dc11': 'http://purl.org/dc/elements/1.1/',
    'oboInOwl': 'http://www.geneontology.org/formats/oboInOwl#',
    'owl': 'http://www.w3.org/2002/07/owl#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
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
