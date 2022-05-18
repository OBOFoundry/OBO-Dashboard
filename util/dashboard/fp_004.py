#!/usr/bin/env python3

## ## [Versioning](http://obofoundry.org/principles/fp-004-versioning.html) Automated Check
##
## Discussion on this check can be [found here](https://github.com/OBOFoundry/OBOFoundry.github.io/issues/1016).
##
## ### Requirements
## 1. The released ontology **must** have a version IRI.
## 2. The version IRI *should* follow a dated format (`NS/YYYY-MM-DD/ontology.owl`)
##
## ### Fixes
## First, make sure you have a valid version IRI pattern. See [Versioning Implementation](http://obofoundry.org/principles/fp-004-versioning.html#implementation) for more details.
##
## #### Adding a Version IRI in Protégé
## The "Ontology Version IRI" input is located in the "Active Ontology" tab that appears when you open your ontology in Protégé.
##
## #### Adding a Version IRI with ROBOT
## You may use the [ROBOT annotate](http://robot.obolibrary.org/annotate) command the add a version IRI.
##
## Please be aware that the [Ontology Development Kit](https://github.com/INCATools/ontology-development-kit) comes standard with a release process that will automatically generate a dated version IRI for your ontology release.
##
## ### Implementation
## The version IRI is retrieved from the ontology using OWL API. For very large ontologies, the RDF/XML ontology header is parsed to find the owl:versionIRI declaration. If found, the IRI is compared to a regex pattern to determine if it is in date format. If it is not in date format, a warning is issued. If the version IRI is not present, this is an error.

from typing import Optional

import dash_utils
import re

import requests

from dash_utils import format_msg

# regex pattern to match dated version IRIs
pat = r'http:\/\/purl\.obolibrary\.org/obo/.*/([0-9]{4}-[0-9]{2}-[0-9]{2})/.*'
PATTERN = re.compile(pat)
#: Official regex for semantic versions from https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$")
#: Regular expression for ISO 8601 compliant date in YYYY-MM-DD format
DATE_PATTERN = re.compile(r"^([0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])$")

# descriptions of issues
bad_format = 'Version IRI \'{0}\' is not in recommended format'
missing_version = 'Missing version IRI'


def has_versioning(ontology):
    """Check fp 4 - versioning.

    Retrieve the version IRI from the OWLOntology object. If the version IRI
    does not exist, ERROR. If the version IRI does exist, check if it is in the
    recommended date format. If not, WARN. Otherwise PASS.

    Args:
        ontology (OWLOntology): ontology object

    Return:
        PASS, INFO, WARN, or ERROR with optional message
    """
    if ontology is None:
        return {'status': 'ERROR', 'comment': 'Unable to load ontology'}

    # retrieve version IRI or None from ontology
    version_iri = dash_utils.get_version_iri(ontology)
    if not version_iri:
        return {'status': 'ERROR', 'comment': missing_version}

    if not url_exists(version_iri):
        return {"status": "ERROR", "comment": "Version IRI does not resolve"}

    iri_version_error_message = get_iri_version_error_message(version_iri)
    if iri_version_error_message is not None:
        return {"status": "ERROR", "comment": iri_version_error_message}

    # compare version IRI to the regex pattern
    if not PATTERN.search(version_iri):
        return {'status': 'WARN',
                'comment': bad_format.format(version_iri)}

    return {'status': 'PASS'}


def big_has_versioning(file):
    """Check fp 4 - versioning.

    This is suitible for large ontologies as it reads the file line by line,
    instead of loading an OWLOntology object. This method looks for the
    owl:versionIRI property in the header.

    Args:
        file (str): path to ontology

    Return:
        PASS, INFO, WARN, or FAIL with optional message
    """
    # may return empty string if version IRI is missing
    # or None if ontology cannot be parsed
    version_iri = dash_utils.get_big_version_iri(file)
    if version_iri is None:
        return {'status': 'ERROR', 'comment': 'Unable to parse ontology'}
    if version_iri == "":
        return {'status': 'ERROR', 'comment': missing_version}
    if not url_exists(version_iri):
        return {"status": "ERROR", "comment": "Version IRI does not resolve"}
    # compare version IRI to the regex pattern
    if not PATTERN.search(version_iri):
        return {'status': 'WARN',
                'comment': bad_format.format(version_iri)}

    return {'status': 'PASS'}


def url_exists(url: str) -> bool:
    # check the URL resolves, but don't download it in full
    # inspired by https://stackoverflow.com/a/61404519/5775947
    try:
        with requests.get(url, stream=True) as res:
            rv = res.status_code == 200
    except Exception:
        # Any errors with connection will be considered
        # as the URL not existing
        return False
    else:
        return rv


def get_iri_version_error_message(version_iri: str) -> Optional[str]:
    """Check a version IRI has exactly one of a semantic version or ISO 8601 date (YYYY-MM-DD) in it."""
    matches_semver = SEMVER_PATTERN.match(version_iri)
    matches_date = DATE_PATTERN.match(version_iri)
    if matches_date and matches_semver:
        return "Version IRI should not contain both a semantic version and date"
    if not matches_date and not matches_semver:
        return "Version IRI has neither a semantic version nor a date"
    # None means it's all gucci
    return None
