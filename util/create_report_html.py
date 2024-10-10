#!/usr/bin/env python3

import argparse
import json
import os
import re
import sys

import pandas as pd
from jinja2 import Template


def main(args):
    """
    """
    parser = argparse.ArgumentParser(description='Create a report HTML page')
    parser.add_argument('report',
                        type=argparse.FileType('r'),
                        help='TSV report to convert to HTML')
    parser.add_argument('context',
                        type=argparse.FileType('r'),
                        help='Ontology prefixes')
    parser.add_argument('template',
                        type=argparse.FileType('r'),
                        help='The template file to use')
    parser.add_argument('title',
                        type=str,
                        help='HTML page title')
    parser.add_argument('outfile',
                        type=argparse.FileType('w'),
                        help='Output report HTML file')
    parser.add_argument('limitlines',
                        type=int,
                        help='Parameter to limit lines', nargs='?', default=50)
    args = parser.parse_args()

    context = json.load(args.context)['@context']

    error_count_rule = {}
    error_count_level = {}
    report_filtered = pd.DataFrame()

    try:
        report = pd.read_csv(args.report, sep="\t")

        # Get sample of each level only for ROBOT report
        if "Level" in report.columns and "Rule Name" in report.columns:
            error_count_level = report["Level"].value_counts()
            error_count_rule = report["Rule Name"].value_counts()

            if error_count_level["ERROR"] < args.limitlines:
                rest = args.limitlines - error_count_level["ERROR"]

                # Calculate the sample number for each level based on group size
                def calculate_sample_size(group, rest):
                    if group["Level"].iloc[0] == "ERROR":
                        return group.shape[0]

                    return min(group.shape[0], rest)

                # Get a sample of each Level type
                report_filtered = report.groupby(by="Level")[
                    ["Level", "Rule Name", "Subject", "Property", "Value"]
                ].apply(
                    lambda x: x.sample(calculate_sample_size(x, rest))
                ).reset_index(drop=True)
            else:
                report_filtered = report.head(args.limitlines)
        else:
            report_filtered = report.head(args.limitlines)

        if len(report_filtered) > args.limitlines:
            report_filtered.to_csv(args.report, sep="\t", index=False)

    except Exception as e:
        print(e)

    # Load Jinja2 template
    template = Template(args.template.read())

    # Generate the HTML output
    res = template.render(contents=report_filtered.reset_index(drop=True),
                          maybe_get_link=maybe_get_link,
                          context=context,
                          title=args.title,
                          file=os.path.basename(args.report.name),
                          error_count_rule=error_count_rule,
                          error_count_level=error_count_level,
                          class_map=class_map
                          )

    args.outfile.write(res)


def maybe_get_link(cell, context):
    """
    Returns an HTML link for the given cell value if it matches certain patterns.

    Args:
        cell (str): The cell value to check for link patterns.
        context (dict): A dictionary containing prefix-context mappings.

    Returns:
        str: An HTML link if a matching pattern is found, otherwise the original cell value.

    """
    url = None
    if cell in report_doc_map:
        # First check if it is a ROBOT report link
        url = report_doc_map[cell]
    else:
        # Otherwise try to parse as CURIE or IRI
        curie = re.search(r'([A-Za-z0-9_]+):([A-Za-z0-9-]+)', cell)
        if curie:
            # This is a CURIE
            prefix = curie.group(1)
            local_id = curie.group(2)
            if prefix in context:
                namespace = context[prefix]["@id"]
                url = namespace + local_id
            elif prefix in other_prefixes:
                namespace = other_prefixes[prefix]
                url = namespace + local_id
        # IRIs might be in angle brackets
        iri = re.search(r'(http://purl.obolibrary.org/obo/[^ <>]+)', cell)
        if iri:
            url = iri.group(1)
    if url:
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{cell}</a>'
    return cell


# CSS classes for each level
class_map = {
    'PASS': 'table-success',
    'INFO': 'table-info',
    'WARN': 'table-warning',
    'ERROR': 'table-danger'
}

other_prefixes = {
    'terms': 'http://purl.org/dc/terms/',
    'dc': 'http://purl.org/dc/elements/1.1/',
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
    'equivalent_class_axiom_no_genus':
        'https://robot.obolibrary.org/report_queries/equivalent_class_axiom_no_genus',
    'equivalent_pair':
        'http://robot.obolibrary.org/report_queries/equivalent_pair',
    'illegal_use_of_built_in_vocabulary':
        'https://robot.obolibrary.org/report_queries/illegal_use_of_built_in_vocabulary',
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
    'missing_subset_declaration':
        'https://robot.obolibrary.org/report_queries/missing_subset_declaration',
    'missing_superclass':
        'http://robot.obolibrary.org/report_queries/missing_superclass',
    'misused_obsolete_label':
        'http://robot.obolibrary.org/report_queries/misused_obsolete_label',
    'misused_replaced_by':
        'https://robot.obolibrary.org/report_queries/misused_replaced_by',
    'multiple_definitions':
        'http://robot.obolibrary.org/report_queries/multiple_definitions',
    'multiple_equivalent_classes':
        'http://robot.obolibrary.org/report_queries/multiple_equivalent_classes',
    'multiple_equivalent_class_definitions':
        'https://robot.obolibrary.org/report_queries/multiple_equivalent_class_definitions',
    'multiple_labels':
        'http://robot.obolibrary.org/report_queries/multiple_labels',
}


if __name__ == '__main__':
    main(sys.argv)
