#!/usr/bin/env python3

import datetime
import gc
import json
import os
import py4j
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

from argparse import ArgumentParser, FileType
from io import TextIOWrapper
from py4j.java_gateway import JavaGateway


def run():
    # ---------------------------- #
    # PREPARE INPUT
    # ---------------------------- #

    # parse input args
    parser = ArgumentParser(description='Create dashboard files')
    parser.add_argument('ontology', type=str, help='Input ontology file')
    parser.add_argument('registry', type=FileType('r'), help='Registry YAML file')
    parser.add_argument('license', type=FileType('r'), help='License JSON schema')
    parser.add_argument('contact', type=FileType('r'), help='Contact JSON schema')
    parser.add_argument('relations', type=FileType('r'), help='Table containing RO IRIs and labels')
    parser.add_argument('outdir', type=str, help='Output directory')
    args = parser.parse_args()

    owl = os.path.basename(args.ontology)
    namespace = os.path.splitext(owl)[0]

    ontology_file = args.ontology
    registry = args.registry
    license_schema = json.load(args.license)
    contact_schema = json.load(args.contact)
    ro_file = args.relations

    # Create the build directory for this ontology
    ontology_dir = args.outdir
    os.makedirs(ontology_dir, exist_ok=True)

    # Launch the JVM using the robot JAR
    py4j.java_gateway.launch_gateway(
        jarpath='build/robot.jar', classpath='org.obolibrary.robot.PythonOperation', die_on_exit=True, port=25333)

    # Activate gateway to JVM
    gateway = JavaGateway()
    robot_gateway = gateway.jvm.org.obolibrary.robot

    # IOHelper for working with ontologies
    io_helper = robot_gateway.IOHelper()

    # Handle ontology file
    big = namespace in BIG_ONTS
    if not big:
        # Load ontology as OWLOntology object
        if not ontology_file:
            ont_or_file = None
        try:
            ont_or_file = io_helper.loadOntology(ontology_file)
        except Exception:
            print('ERROR: Unable to load \'{0}\''.format(ontology_fil), flush=True)
            ont_or_file = None
        # Get the Verison IRI
        version_iri = dash_utils.get_version_iri(ont_or_file)
    else:
        # Just provide path to file
        ont_or_file = ontology_file
        # Get the version IRI by text parsing
        version_iri = dash_utils.get_big_version_iri(ont_or_file)

    # Get the registry data
    yaml_data = yaml.load(registry, Loader=yaml.SafeLoader)
    yaml_data = yaml_data['ontologies']
    data = dash_utils.get_data(namespace, yaml_data)

    # Map of all ontologies to their domains
    domain_map = dash_utils.get_domains(yaml_data)
    # Map of RO labels to RO IRIs
    ro_props = fp_007.get_ro_properties(ro_file)

    if 'is_obsolete' in data and data['is_obsolete'] is 'true':
        # do not run on obsolete ontologies
        print('{0} is obsolete and will not be checked...'.format(namespace), flush=True)
        sys.exit(0)

    # ---------------------------- #
    # RUN CHECKS
    # ---------------------------- #

    print('-----------------\nChecking ' + namespace, flush=True)

    # Get the report based on if it's big or not
    report = None
    good_format = None
    if big:
        if namespace != 'gaz':
            # Report currently takes TOO LONG for GAZ
            print('Running ROBOT report on {0}...'.format(namespace), flush=True)
            report_obj = report_utils.BigReport(robot_gateway, namespace, ont_or_file)
            report = report_obj.get_report()
            good_format = report_obj.get_good_format()
    else:
        if ont_or_file:
            # Ontology is not None
            print('Running ROBOT report on {0}...'.format(namespace), flush=True)
            report = report_utils.run_report(robot_gateway, io_helper, ont_or_file)

    # Execute the numbered checks
    check_map = {}
    try:
        if big:
            check_map[1] = fp_001.big_is_open(ont_or_file, data, license_schema)
        else:
            check_map[1] = fp_001.is_open(ont_or_file, data, license_schema)
    except Exception as e:
        check_map[1] = 'INFO|unable to run check 1'
        print('ERROR: unable to run check 1 for {0}\nCAUSE:\n{1}'.format(namespace, str(e)), flush=True)

    try:
        if big:
            check_map[2] = fp_002.big_is_common_format(good_format)
        else:
            check_map[2] = fp_002.is_common_format(ont_or_file)
    except Exception as e:
        check_map[2] = 'INFO|unable to run check 2'
        print('ERROR: unable to run check 2 for {0}\nCAUSE:\n{1}'.format(namespace, str(e)), flush=True)

    try:
        if big:
            check_map[3] = fp_003.big_has_valid_uris(namespace, ont_or_file, ontology_dir)
        else:
            check_map[3] = fp_003.has_valid_uris(robot_gateway, namespace, ont_or_file, ontology_dir)
    except Exception as e:
        check_map[3] = 'INFO|unable to run check 3'
        print('ERROR: unable to run check 3 for {0}\nCAUSE:\n{1}'.format(namespace, str(e)), flush=True)

    try:
        if big:
            check_map[4] = fp_004.big_has_versioning(ont_or_file)
        else:
            check_map[4] = fp_004.has_versioning(ont_or_file)
    except Exception as e:
        check_map[4] = 'INFO|unable to run check 4'
        print('ERROR: unable to run check 4 for {0}\nCAUSE:\n{1}'.format(namespace, str(e)), flush=True)

    try:
        check_map[5] = fp_005.has_scope(data, domain_map)
    except Exception as e:
        check_map[5] = 'INFO|unable to run check 5'
        print('ERROR: unable to run check 5 for {0}\nCAUSE:\n{1}'.format(namespace, str(e)), flush=True)

    try:
        check_map[6] = fp_006.has_valid_definitions(report)
    except Exception as e:
        check_map[6] = 'INFO|unable to run check 6'
        print('ERROR: unable to run check 6 for {0}\nCAUSE:\n{1}'.format(namespace, str(e)), flush=True)

    try:
        if big:
            check_map[7] = fp_007.big_has_valid_relations(namespace, ont_or_file, ro_props, ontology_dir)
        else:
            check_map[7] = fp_007.has_valid_relations(namespace, ont_or_file, ro_props, ontology_dir)
    except Exception as e:
        check_map[7] = 'INFO|unable to run check 7'
        print('ERROR: unable to run check 7 for {0}\nCAUSE:\n{1}'.format(namespace, str(e)), flush=True)

    try:
        check_map[8] = fp_008.has_documentation(data)
    except Exception as e:
        check_map[8] = 'INFO|unable to run check 8'
        print('ERROR: unable to run check 8 for {0}\nCAUSE:\n{1}'.format(namespace, str(e)), flush=True)

    try:
        check_map[9] = fp_009.has_users(data)
    except Exception as e:
        check_map[9] = 'INFO|unable to run check 9'
        print('ERROR: unable to run check 9 for {0}\nCAUSE:\n{1}'.format(namespace, str(e)), flush=True)

    try:
        check_map[11] = fp_011.has_contact(data, contact_schema)
    except Exception as e:
        check_map[11] = 'INFO|unable to run check 11'
        print('ERROR: unable to run check 11 for {0}\nCAUSE:\n{1}'.format(namespace, str(e)), flush=True)

    try:
        check_map[12] = fp_012.has_valid_labels(report)
    except Exception as e:
        check_map[12] = 'INFO|unable to run check 12'
        print('ERROR: unable to run check 12 for {0}\nCAUSE:\n{1}'.format(namespace, str(e)), flush=True)

    try:
        if big:
            check_map[16] = fp_016.big_is_maintained(ont_or_file)
        else:
            check_map[16] = fp_016.is_maintained(ont_or_file)
    except Exception as e:
        check_map[16] = 'INFO|unable to run check 16'
        print('ERROR: unable to run check 16 for {0}\nCAUSE:\n{1}'.format(namespace, str(e)), flush=True)

    # finally, add the report results to the dashboard and save the report
    try:
        check_map['report'] = report_utils.process_report(robot_gateway, report, ontology_dir)
    except Exception as e:
        check_map['report'] = 'INFO|unable to save report'
        print('ERROR: unable to save ROBOT report for {0}\nCAUSE:\n{1}'.format(namespace, str(e)), flush=True)

    # ---------------------------- #
    # SAVE RESULTS
    # ---------------------------- #

    # Parse results
    err = 0
    warn = 0
    info = 0
    all_checks = {}

    for check, result in check_map.items():
        if result is None or 'status' not in result:
            print('Missing result for check {0}'.format(check), flush=True)
            continue

        status = result['status']

        if status == 'ERROR':
            err += 1
        elif status == 'WARN':
            warn += 1
        elif status == 'INFO':
            info += 1
        elif status != 'PASS':
            print('Unknown status "{0}" for check {1}'.format(status, check), flush=True)
            continue

        key = check
        if check in PRINCIPLE_MAP:
            key = PRINCIPLE_MAP[check]
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
    save_data = {'namespace': namespace, 'version': version_iri, 'date': date.strftime('%Y-%m-%d'),
                 'summary': {'status': summary, 'comment': summary_comment}, 'results': all_checks}

    # Save to YAML file
    outfile = os.path.join(ontology_dir, 'dashboard.yml')
    print('Saving results to {0}'.format(outfile))
    with open(outfile, 'w+') as f:
        yaml.dump(save_data, f)

    sys.exit(0)


BIG_ONTS = ['bto', 'chebi', 'dron', 'gaz', 'ncbitaxon', 'ncit', 'pr', 'uberon']
OBO = 'http://purl.obolibrary.org/obo'

PRINCIPLE_MAP = {
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


if __name__ == '__main__':
    run()
