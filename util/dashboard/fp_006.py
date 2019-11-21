#!/usr/bin/env python3

## ## "Textual Definitions" Automated Check
##
## ### Requirements
## 1. Each definition **must** be unique.
## 2. Each entity **must** not have more than one textual definition.
## 3. Each entity *should* have a textual definition using [IAO:0000115 (definition)](http://purl.obolibrary.org/obo/IAO_0000115).
##
## ### Implementation
## [ROBOT report](http://robot.obolibrary.org/report) is run over the ontology. A count of violations for each of the following checks is retrieved from the report object: [duplicate definition](http://robot.obolibrary.org/report_queries/duplicate_definition), [multiple definitions](http://robot.obolibrary.org/report_queries/multiple_definitions), and [missing definition](http://robot.obolibrary.org/report_queries/missing_definition). If there are any duplicate or multiple defintions, it is an error. If there are missing definitions, it is a warning.

import dash_utils
from dash_utils import format_msg


def has_valid_definitions(report):
    """Check fp 6 - textual definitions.

    If the ontology passes all ROBOT report definition checks, PASS. If there
    are any violations, return that level of violation and a summary of the
    violations.

    Args:
        report (Report): ROBOT report object
    """
    if report is None:
        return {'status': 'INFO', 'comment': 'Report could not be generated'}

    # error level violations
    duplicates = report.getViolationCount('duplicate_definition')
    multiples = report.getViolationCount('multiple_definitions')

    # warn level violation
    missing = report.getViolationCount('missing_definition')

    if duplicates > 0 and multiples > 0 and missing > 0:
        return {'status': 'ERROR',
                'comment': ' '.join([duplicate_msg.format(duplicates),
                                     multiple_msg.format(multiples),
                                     missing_msg.format(missing),
                                     help_msg])}
    elif duplicates > 0 and multiples > 0:
        return {'status': 'ERROR',
                'comment': ' '.join([duplicate_msg.format(duplicates),
                                     multiple_msg.format(multiples),
                                     help_msg])}
    elif duplicates > 0 and missing > 0:
        return {'status': 'ERROR',
                'comment': ' '.join([duplicate_msg.format(duplicates),
                                     missing_msg.format(missing),
                                     help_msg])}
    elif multiples > 0 and missing > 0:
        return {'status': 'ERROR',
                'comment': ' '.join([multiple_msg.format(multiples),
                                     missing_msg.format(missing),
                                     help_msg])}
    elif duplicates > 0:
        return {'status': 'ERROR',
                'comment': ' '.join([duplicate_msg.format(duplicates),
                                     help_msg])}
    elif multiples > 0:
        return {'status': 'ERROR',
                'comment': ' '.join([multiple_msg.format(missing),
                                     help_msg])}
    elif missing > 0:
        return {'status': 'WARN',
                'comment': ' '.join([missing_msg.format(missing),
                                     help_msg])}
    else:
        # no violations found
        return {'status': 'PASS'}


# violation messages
duplicate_msg = '{0} duplicate definitions.'
multiple_msg = '{0} multiple definitions.'
missing_msg = '{0} missing definitions.'
help_msg = 'See ROBOT Report for details.'
