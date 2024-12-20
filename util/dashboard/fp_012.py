#!/usr/bin/env python3

## ## [Naming Conventions](http://obofoundry.org/principles/fp-012-naming-conventions.html) Automated Check
##
## Discussion on this check can be [found here](https://github.com/OBOFoundry/OBOFoundry.github.io/issues/1006).
##
## ### Requirements
##
## 1. Each label **must** be unique.
## 2. Each entity **must** not have more than one label.
## 3. Each entity _should_ have a label using `rdfs:label`.
##
## ### Fixes
##
## #### Uniqueness
##
## Update at least one label to distinguish between the two terms. Add the original label to a `oboInOwl:hasExactSynonym` (alternatively, narrow, related, or broad) or [`IAO:0000118` (alternative term)](http://purl.obolibrary.org/obo/IAO_0000118) annotation.
##
## If the terms are exactly the same:
##
## 1. Obsolete one of them by adding the `owl:deprecated` annotation property with a boolean value of `true`
## 2. Add `obsolete` to the beginning of this term's label
## 3. Add a [`IAO:0100001` (term replaced by)](http://purl.obolibrary.org/obo/IAO_0100001) annotation to this term pointing to the other, non-deprecated term.
##    - Make sure this is an IRI annotation by selecting "IRI Editor" when adding the annotation in Protégé
##
## #### Multiple Labels
##
## Determine which label most accurately describes the term. Change the other label(s) to `oboInOwl:hasExactSynonym` (alternatively, narrow, related, or broad) or [`IAO:0000118` (alternative term)](http://purl.obolibrary.org/obo/IAO_0000118).
##
## #### Missing Labels
##
## Add an `rdfs:label` annotation to each term that is missing a label. For adding labels in bulk, check out [ROBOT template](http://robot.obolibrary.org/template).
##
## ### Implementation
##
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
