#!/usr/bin/env python3

import datetime
import gc
import json
import os
import pprint
import sys
import yaml

import dash_utils
import fp_001
import fp_002
import fp_003
import fp_004
import fp_005
import fp_006
import fp_007
import fp_008
import fp_009
import fp_011
import fp_012
import fp_016
import report_utils

from argparse import ArgumentParser
from py4j.java_gateway import JavaGateway
from py4j.protocol import Py4JNetworkError

big_onts = ['chebi', 'bto', 'uberon', 'ncbitaxon', 'pr', 'ncit', 'gaz']
obo = 'http://purl.obolibrary.org/obo'

principle_map = {
    1: 'FP1 Open',
    2: 'FP2 Common Format',
    3: 'FP3 URIs',
    4: 'FP4 Versioning',
    5: 'FP5 Scope',
    6: 'FP6 Textual Definitions',
    7: 'FP7 Relations',
    8: 'FP8 Documented',
    9: 'FP9 Plurality of Users',
    11: 'FP11 Locus of Authority',
    12: 'FP12 Naming Conventions',
    16: 'FP16 Maintenance'
}


def main(args):
    """Usage: ./dashboard.py <ontologies_yml> <output_csv> [--big <bool>]

    Create a dashboard CSV over the ontologies in the registry data. If --big,
    only do the "big" ontologies (which need different processing). Otherwise,
    ignore "big" ontologies.
    """
    global domain_map, gateway, io_helper, robot_gateway, ro_props, version_iri

    # parse input args
    parser = ArgumentParser(description='Create a dashboard file')
    parser.add_argument('namespace',
                        type=str,
                        help='Ontology namespace to run dashboard on')
    parser.add_argument('registry_yaml',
                        type=str,
                        help='Ontology registry data')
    parser.add_argument('ro',
                        type=str,
                        help='Path to RO ontology file')
    parser.add_argument('out_dir',
                        type=str,
                        help='Dashboard output directory')
    args = parser.parse_args()

    # activate gateway to JVM
    try:
        gateway = JavaGateway()
        robot_gateway = gateway.jvm.org.obolibrary.robot
    except Py4JNetworkError:
        print('ERROR: No JVM listening on port 25333', flush=True)
        sys.exit(1)
    except Exception as e:
        print('ERROR: problem with JVM on port 25333\n{0}'.format(str(e)),
              flush=True)
        sys.exit(1)

    # IOHelper for working with ontologies
    io_helper = robot_gateway.IOHelper()

    # IO files
    namespace = args.namespace
    yaml_infile = args.registry_yaml
    out_dir = args.out_dir
    outfile = '{0}/dashboard.yml'.format(out_dir)

    # Maybe run special "big" checks
    big = False
    if namespace in big_onts:
        big = True

    # Load the data
    all_data = load_data(yaml_infile)
    data = get_data(namespace, all_data)

    # Get all other registry domains to compare to this ontology domain
    domain_map = get_domains(all_data)

    # RO properties for relations check
    ro = load_ontology_from_file(args.ro)
    ro_props = fp_007.get_properties('ro', ro)

    # Remove RO from memory
    del ro

    # Run checks and save results
    res = exec_checks(namespace, data, big)
    save_results(namespace, res, outfile)

    # clean up
    gc.collect()
    sys.exit(0)


def exec_checks(ns, data, big):
    """
    """
    global version_iri

    version_iri = None

    if 'is_obsolete' in data and data['is_obsolete'] is 'true':
        # do not run on obsolete ontologies
        print('{0} is obsolete and will not be checked...'.format(ns),
              flush=True)
        gc.collect()
        sys.exit(0)
    try:
        print('\n-----------------\nChecking ' + ns, flush=True)
        if big:
            file = download_ontology(ns)
            if file:
                version_iri = dash_utils.get_big_version_iri(file)
            return big_check_principles(file, ns, data)
        else:
            ont_file = fetch_base_ontology(ns)
            ont = load_ontology_from_file(ont_file)
            if ont:
                version_iri = dash_utils.get_version_iri(ont)
            return check_principles(ont, ns, data)
    except Exception as e:
        # Could not complete, exit with status 1
        print(
            'ERROR: Unable to finish check on {0}\nCAUSE:\n{1}'.format(
                ns, str(e)),
            flush=True)
        sys.exit(1)


def check_principles(ont, ns, data):
    """Given an ontology ID and the corresponding data from the YAML,
    run the automated principle validation. Return a map of results.
    """
    if ont:
        print('Running ROBOT report on {0}...'.format(ns), flush=True)
        report = report_utils.run_report(robot_gateway, io_helper, ns, ont)
    else:
        report = None

    # run each principle check
    check_map = run_checks(robot_gateway, ns, ont, None, report, data, None)

    # remove from memory
    del report
    del ont

    return check_map


def big_check_principles(file, ns, data):
    """Given an ontology ID and the corresponding data from the YAML,
    run the automated principle validation. Return a map of results.
    """
    print('Running ROBOT report on {0}...'.format(ns), flush=True)
    report_obj = report_utils.BigReport(robot_gateway, ns, file)
    report = report_obj.get_report()
    good_format = report_obj.get_good_format()

    # run each principle check
    check_map = run_checks(
        robot_gateway, ns, None, file, report, data, good_format)

    # remove from memory
    del report_obj
    del report

    return check_map


def run_checks(robot_gateway, ns, ont, file, report, data, good_format):
    """Given a robot gateway, an ontology namespace, an ontology object (or
    None), a path to ontology (or None), a ROBOT report object, the
    registry data, and a boolean indicating good formatting for large
    ontologies (None for regular ontologies), run all the principle checks and
    return a map with results.
    """
    check_map = {}

    try:
        if file:
            check_map[1] = fp_001.big_is_open(file, data)
        else:
            check_map[1] = fp_001.is_open(ont, data)
    except Exception as e:
        check_map[1] = 'INFO|unable to run check 1'
        print('ERROR: unable to run check 1 for {0}\nCAUSE:\n{1}'.format(
                  ns, str(e)),
              flush=True)

    try:
        if file:
            check_map[2] = fp_002.big_is_common_format(good_format)
        else:
            check_map[2] = fp_002.is_common_format(ont)
    except Exception as e:
        check_map[2] = 'INFO|unable to run check 2'
        print('ERROR: unable to run check 2 for {0}\nCAUSE:\n{1}'.format(
                  ns, str(e)),
              flush=True)

    try:
        if file:
            check_map[3] = fp_003.big_has_valid_uris(ns, file)
        else:
            check_map[3] = fp_003.has_valid_uris(robot_gateway, ns, ont)
    except Exception as e:
        check_map[3] = 'INFO|unable to run check 3'
        print('ERROR: unable to run check 3 for {0}\nCAUSE:\n{1}'.format(
                  ns, str(e)),
              flush=True)

    try:
        if file:
            check_map[4] = fp_004.big_has_versioning(file)
        else:
            check_map[4] = fp_004.has_versioning(ont)
    except Exception as e:
        check_map[4] = 'INFO|unable to run check 4'
        print('ERROR: unable to run check 4 for {0}\nCAUSE:\n{1}'.format(
                  ns, str(e)),
              flush=True)

    try:
        check_map[5] = fp_005.has_scope(data, domain_map)
    except Exception as e:
        check_map[5] = 'INFO|unable to run check 5'
        print('ERROR: unable to run check 5 for {0}\nCAUSE:\n{1}'.format(
                  ns, str(e)),
              flush=True)

    try:
        check_map[6] = fp_006.has_valid_definitions(report)
    except Exception as e:
        check_map[6] = 'INFO|unable to run check 6'
        print('ERROR: unable to run check 6 for {0}\nCAUSE:\n{1}'.format(
                  ns, str(e)),
              flush=True)

    try:
        if file:
            check_map[7] = fp_007.big_has_valid_relations(ns, file, ro_props)
        else:
            check_map[7] = fp_007.has_valid_relations(ns, ont, ro_props)
    except Exception as e:
        check_map[7] = 'INFO|unable to run check 7'
        print('ERROR: unable to run check 7 for {0}\nCAUSE:\n{1}'.format(
                  ns, str(e)),
              flush=True)

    try:
        check_map[8] = fp_008.has_documentation(data)
    except Exception as e:
        check_map[8] = 'INFO|unable to run check 8'
        print('ERROR: unable to run check 8 for {0}\nCAUSE:\n{1}'.format(
                  ns, str(e)),
              flush=True)

    try:
        check_map[9] = fp_009.has_users(data)
    except Exception as e:
        check_map[9] = 'INFO|unable to run check 9'
        print('ERROR: unable to run check 9 for {0}\nCAUSE:\n{1}'.format(
                  ns, str(e)),
              flush=True)

    try:
        check_map[11] = fp_011.has_contact(data)
    except Exception as e:
        check_map[11] = 'INFO|unable to run check 11'
        print('ERROR: unable to run check 11 for {0}\nCAUSE:\n{1}'.format(
                  ns, str(e)),
              flush=True)

    try:
        check_map[12] = fp_012.has_valid_labels(report)
    except Exception as e:
        check_map[12] = 'INFO|unable to run check 12'
        print('ERROR: unable to run check 12 for {0}\nCAUSE:\n{1}'.format(
                  ns, str(e)),
              flush=True)

    try:
        if file:
            check_map[16] = fp_016.big_is_maintained(file)
        else:
            check_map[16] = fp_016.is_maintained(ont)
    except Exception as e:
        check_map[16] = 'INFO|unable to run check 16'
        print('ERROR: unable to run check 16 for {0}\nCAUSE:\n{1}'.format(
                  ns, str(e)),
              flush=True)

    # finally, add the report results to the dashboard
    try:
        check_map['report'] = report_utils.process_report(
            robot_gateway, ns, report)
    except Exception as e:
        check_map['report'] = 'INFO|unable to save report'
        print('ERROR: unable to save ROBOT report for {0}\nCAUSE:\n{1}'.format(
                  ns, str(e)),
              flush=True)

    return check_map


def save_results(namespace, check_map, outfile):
    """
    """
    global version_iri

    lines = []

    # Track overall status
    err = 0
    warn = 0
    info = 0

    all_checks = {}

    for check, result in check_map.items():
        if result is None or 'status' not in result:
            print('Missing result for check {0}'.format(check),
                  flush=True)
            continue

        status = result['status']

        if status == 'ERROR':
            err += 1
        elif status == 'WARN':
            warn += 1
        elif status == 'INFO':
            info += 1
        elif status != 'PASS':
            print('Unknown status "{0}" for check {1}'.format(status, check),
                  flush=True)
            continue

        key = check
        if check in principle_map:
            key = principle_map[check]
        elif check == 'report':
            key = 'ROBOT Report'

        all_checks[key] = result

    # Summary status
    if err > 0:
        summary = 'ERROR'
        summary_comment = '{0} errors'.format(err)
    elif warn > 0:
        summary = 'WARN'
        summary_comment = '{0} warnings'.format(warn)
    elif info > 0:
        summary = 'INFO'
        summary_comment = '{0} info messages'.format(info)
    else:
        summary = 'PASS'
        summary_comment = ''

    date = datetime.datetime.today()

    data = {}
    data['namespace'] = namespace
    data['version'] = version_iri
    data['date'] = date.strftime('%Y-%m-%d')
    data['summary'] = {'status': summary, 'comment': summary_comment}
    data['results'] = all_checks

    print('Saving results to {0}'.format(outfile))

    with open(outfile, 'w+') as f:
        yaml.dump(data, f)


def load_data(yaml_infile):
    """Given the registry YAML file, load the data.
    Return a map of ontology ID to data item.
    """
    with open(yaml_infile, 'r') as s:
        data = yaml.load(s, Loader=yaml.SafeLoader)
    return data['ontologies']


def get_data(namespace, all_data):
    """Given the ontology data from the registry YAML file,
    and an ontology namespace, return the data for that namespace.
    """
    data_map = {}
    for item in all_data:
        ont_id = item['id']
        if ont_id.lower() == namespace.lower():
            return item
    return None


def get_domains(ont_data):
    """Given the ontology data fro the registry YAML file,
    map the ontology ID to the scope (domain).
    """
    domain_map = {}
    for item in ont_data:
        ont_id = item['id']
        if 'domain' in item:
            domain_map[ont_id] = item['domain']
    return domain_map


def fetch_base_ontology(ns):
    """Given a namespace, use ROBOT to create a 'base' artefact that only
    contains internal terms. Save this fiile in the build directory.
    """
    # NS with lowercase letters
    if ns == 'ncbitaxon':
        ns = 'NCBITaxon'
    elif ns == 'fbdv':
        ns = 'FBdv'
    elif ns == 'mirnao':
        ns = 'miRNAO'
    elif ns == 'vario':
        ns = 'VariO'
    elif ns == 'wbbt':
        ns = 'WBbt'
    elif ns == 'wbphenotype':
        ns = 'WBPhenotype'
    else:
        ns = ns.upper()

    # option args
    purl = '{0}/{1}.owl'.format(obo, ns.lower())
    base = '{0}/{1}_'.format(obo, ns)
    output = 'build/ontologies/{0}.owl'.format(ns.lower())

    # easier to do this via command line
    cmd = '''java -jar build/robot-foreign.jar merge --input-iri {0} \
             remove --base-iri {1} --axioms external \
             -p false --output {2}'''.format(purl, base, output)
    os.system(cmd)

    if not os.path.isfile(output):
        print('ERROR: Unable to retrieve {0}'.format(ns), flush=True)
        return None
    return output


def load_ontology_from_file(path):
    """Given a path to an ontology file, load the file as an OWLOntology.
    """
    if not path:
        return None
    ont = None
    try:
        ont = io_helper.loadOntology(path)
    except Exception as e:
        print('ERROR: Unable to load \'{0}\''.format(path), flush=True)
        return None
    return ont


def load_ontology_from_iri(purl):
    """Given a PURL, return an OWLOntology object.
    """
    iri = gateway.jvm.org.semanticweb.owlapi.model.IRI.create(purl)
    ont = None
    try:
        ont = io_helper.loadOntology(iri)
    except Exception as e:
        print('ERROR: Unable to load <{0}>'.format(purl), flush=True)
        return None
    return ont


def download_ontology(ns):
    """Given a PURL, download the ontology to a file in the build directory.
    """
    purl = '{0}/{1}.owl'.format(obo, ns.lower())
    file = 'build/ontologies/{0}.owl'.format(ns)
    if not os.path.isfile(file):
        curl = 'curl -Lk {0} > {1}'.format(purl, file)
        os.system(curl)
    if not os.path.isfile(file):
        print('ERROR: Unable to download {0}'.format(ns), flush=True)
        return None
    return file


if __name__ == '__main__':
    main(sys.argv)
