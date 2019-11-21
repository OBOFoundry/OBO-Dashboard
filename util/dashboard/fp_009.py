#!/usr/bin/env python3

## ## "Plurality of Users" Automated Check
##
## ### Requirements
## 1. The ontology **must** have a tracker.
## 2. The ontology **must** have usages.
##
## ### Implementation
## The registry data is checked for 'tracker' and 'usage' entries. If either is missing, this is an error.

import dash_utils
from dash_utils import format_msg


def has_users(data):
    """Check fp 9 - users.
    If the ontology has an active issue tracker and examples of use, PASS.

    Args:
        data (dict): ontology registry data from YAML file

    Return:
        PASS or ERROR with optional help message
    """
    if 'tracker' in data:
        tracker = data['tracker']
    else:
        tracker = None
    if 'usages' in data:
        usages = data['usages']
        # TODO: usages should have a valid user that resovles
        #       and a description
    else:
        usages = None

    # tracker is required?
    if tracker is None and usages is None:
        return {'status': 'ERROR', 'comment': 'Missing tracker and usages'}
    elif tracker is None:
        return {'status': 'ERROR', 'comment': 'Missing tracker'}
    elif usages is None:
        return {'status': 'ERROR', 'comment': 'Missing usages'}
    return {'status': 'PASS'}
