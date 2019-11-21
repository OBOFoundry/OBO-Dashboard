#!/usr/bin/env python3

## ## "Naming Conventions" Automated Check
##
## ### Requirements
## 1. Each label **must** be unique.
## 2. Each entity **must** not have more than one label.
## 3. Each entity *should* have a label using `rdfs:label`.
##
## ### Implementation
## [ROBOT report](http://robot.obolibrary.org/report) is run over the ontology. A count of violations for each of the following checks is retrieved from the report object: [duplicate label](http://robot.obolibrary.org/report_queries/duplicate_label), [multiple labels](http://robot.obolibrary.org/report_queries/multiple_labels), and [missing label](http://robot.obolibrary.org/report_queries/missing_label). If there are any of these violations, it is an error.

import dash_utils
from dash_utils import format_msg


def has_valid_labels(report):
    """Check fp 12 - naming conventions.

    If the ontology passes all ROBOT report label checks, return PASS.

    Args:
        report (Report): complete ROBOT report

    Return:
        PASS, INFO, or ERROR with optional help message
    """
    if report is None:
        return {'status': 'INFO',
                'comment': 'ROBOT Report could not be generated'}

    # all error level
    duplicates = report.getViolationCount('duplicate_label')
    missing = report.getViolationCount('missing_label')
    multiples = report.getViolationCount('multiple_labels')

    if duplicates > 0 and multiples > 0 and missing > 0:
        # all three violations
        return {'status': 'ERROR',
                'comment': ' '.join([duplicate_msg.format(duplicates),
                                     multiple_msg.format(multiples),
                                     missing_msg.format(missing),
                                     help_msg])}
    elif duplicates > 0 and multiples > 0:
        # duplicate and multiple labels
        return {'status': 'ERROR',
                'comment': ' '.join([duplicate_msg.format(duplicates),
                                     multiple_msg.format(multiples),
                                     help_msg])}
    elif duplicates > 0 and missing > 0:
        # duplicate and missing labels
        return {'status': 'ERROR',
                'comment': ' '.join([duplicate_msg.format(duplicates),
                                     missing_msg.format(missing),
                                     help_msg])}
    elif multiples > 0 and missing > 0:
        # multiple and missing labels
        return {'status': 'ERROR',
                'comment': ' '.join([multiple_msg.format(multiples),
                                     missing_msg.format(missing),
                                     help_msg])}
    elif duplicates > 0:
        # just duplicate labels
        return {'status': 'ERROR',
                'comment': ' '.join([duplicate_msg.format(duplicates),
                                     help_msg])}
    elif multiples > 0:
        # just multiple labels
        return {'status': 'ERROR',
                'comment': ' '.join([multiple_msg.format(multiples),
                                     help_msg])}
    elif missing > 0:
        # just missing labels
        return {'status': 'ERROR',
                'comment': ' '.join([missing_msg.format(missing),
                                     help_msg])}
    else:
        # no label violations present
        return {'status': 'PASS'}


# violation messages
duplicate_msg = '{0} duplicate labels.'
multiple_msg = '{0} multiple labels.'
missing_msg = '{0} missing labels.'
help_msg = 'See ROBOT Report for details.'
