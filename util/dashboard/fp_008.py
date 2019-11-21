#!/usr/bin/env python3

## ## "Documented" Automated Check
##
## ### Requirements
## 1. The ontology **must** have a homepage.
## 2. The ontology **must** have a description.
##
## ### Implementation
## The registry data is checked for 'homepage' and 'description' entries. If either is missing, this is an error. If the homepage is present, the URL is checked to see if it resolves (does not return an HTTP status of greater than 400). If the URL does not resolve, this is also an error.

import requests


def has_documentation(data):
    """Check fp 8 - documentation.

    If the ontology has a valid homepage and description, return PASS. The
    homepage URL must also resolve.

    Args:
        data (dict): ontology registry data from YAML file

    Return:
        PASS or ERROR with optional help message
    """
    # check if the data exists
    if 'homepage' in data:
        home = data['homepage']
    else:
        home = None
    if 'description' in data:
        descr = data['description']
    else:
        descr = None

    if home is None and descr is None:
        return {'status': 'ERROR',
                'comment': 'Missing homepage and description'}
    elif home is None:
        return {'status': 'ERROR',
                'comment': 'Missing homepage'}
    elif descr is None:
        return {'status': 'ERROR',
                'comment': 'Missing description'}

    # check if URL resolves
    try:
        request = requests.get(home)
    except Exception as e:
        return {'status': 'ERROR',
                'comment': 'homepage URL ({0}) does not resolve'.format(home)}
    if request.status_code > 400:
        return {'status': 'ERROR',
                'comment': 'homepage URL ({0}) does not resolve'.format(home)}
    return {'status': 'PASS'}
