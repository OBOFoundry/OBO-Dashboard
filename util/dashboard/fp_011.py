#!/usr/bin/env python3

## ## "Locus of Authority" Automated Check
##
## ### Requirements
## 1. The ontology **must** have a single contact person
##
## ### Implementation
## The registry data entry is validated with JSON schema using the [contact schema](https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/util/schema/contact.json). The contact schema ensures that a contact entry is present and that the entry has a name and email address.

import jsonschema

import dash_utils
from dash_utils import format_msg

contact_schema = dash_utils.load_schema('dependencies/contact.json')


def has_contact(data):
    """Check fp 11 - locus of authority.

    Check if the registry data contains a valid contract entry.

    Args:
        data (dict): ontology registry data from YAML file

    Return:
        PASS or ERROR with optional help message
    """
    try:
        jsonschema.validate(data, contact_schema)
    except jsonschema.exceptions.ValidationError as ve:
        if 'contact' in data:
            # contact is in data but is not proper format
            return {'status': 'ERROR',
                    'comment': 'Invalid contact information'}
        else:
            # contact entry is missing from data
            return {'status': 'ERROR',
                    'comment': 'Missing contact information'}
    return {'status': 'PASS'}
