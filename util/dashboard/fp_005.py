#!/usr/bin/env python

## ## [Scope](http://obofoundry.org/principles/fp-005-delineated-content.html) Automated Check
##
## Discussion on this check can be [found here](https://github.com/OBOFoundry/OBOFoundry.github.io/issues/1015).
##
## ### Requirements
##
## 1. A scope ('domain') **must** be declared in the registry data
##
## ### Fixes
##
## First, read the [FAQ](http://obofoundry.github.io/faq/how-do-i-edit-metadata.html) on how to edit the metadata for your ontology. Then, add the following to your [metadata file](https://github.com/OBOFoundry/OBOFoundry.github.io/tree/master/ontology) (replacing with your domain):
##
## ```
## domain: experiments
## ```
##
## ### Implementation
##
## First, the registry data is checked for a 'domain' tag. If missing, that is an error. If it is present, the domain is compared to all other ontology domains. If the ontology shares a domain with one or more other ontologies, we return a list of those ontologies in an info message.

import dash_utils
from dash_utils import format_msg

info_msg = 'Shares domain \'{0}\' with {1} other ontologies ({2})'


def has_scope(data, domain_map):
    '''Check fp 5 - scope.

    Retrieve the "scope" tag from the data and compare to other scopes in the
    map. If domains overlap, return INFO with a list of overlapping domains.
    If scope is missing, ERROR. Otherwise, PASS.

    Args:
        data (dict): ontology data from registry
        domain_map (dict): map of ontology to domain
    '''
    ns = data['id']
    if 'domain' in data:
        domain = data['domain']
    else:
        return {'status': 'ERROR', 'comment': 'Missing domain (scope)'}

    # This check is excluded for now
    # exclude this NS from check (it will match itself)
    # updated_domain_map = domain_map
    # updated_domain_map.pop(ns)
    # if domain in updated_domain_map.values():
    # same_domain = []
    # for ont_id, other_domain in domain_map.items():
    # if domain == other_domain:
    # same_domain.append(ont_id)
    # same_domain_str = ', '.join(same_domain)
    # return {'status': 'INFO',
    # 'comment': info_msg.format(
    # domain, len(same_domain), same_domain_str)}

    return {'status': 'PASS'}
