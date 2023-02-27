#!/usr/bin/env python3

import datetime
import json
import os
import py4j
import sys
import yaml
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

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
import fp_020
import report_utils

logging.basicConfig(level=logging.INFO)

from argparse import ArgumentParser, FileType
from py4j.java_gateway import JavaGateway
from lib import round_float, compute_dashboard_score_alt1, compute_obo_score, DashboardConfig, \
    create_dashboard_score_badge, create_dashboard_qc_badge


def run():
    # ---------------------------- #
    # PREPARE INPUT
    # ---------------------------- #

    # parse input args
    parser = ArgumentParser(description='Create dashboard files')
    parser.add_argument('ontology', type=str, help='Input ontology file')
    parser.add_argument('ontologymetrics', type=str, help='Output from ROBOT metrics run')
    parser.add_argument('registry', type=FileType('r'), help='Registry YAML file')
    parser.add_argument('schema', type=FileType('r'), help='OBO JSON schema')
    parser.add_argument('relations', type=FileType('r'), help='Table containing RO IRIs and labels')
    parser.add_argument('profile', type=str, help='Optional location of profile.txt file.')
    parser.add_argument('configfile', type=str, help='Location of the dashboard config file', default='build/robot.jar')
    parser.add_argument('outdir', type=str, help='Output directory')
    parser.add_argument('robot_jar',type=str,help='Location of your local ROBOT jar', default='build/robot.jar')
    args = parser.parse_args()

    config = DashboardConfig(args.configfile)
    owl = os.path.basename(args.ontology)
    namespace = os.path.splitext(owl)[0]

    ontology_file = args.ontology
    metrics_file = args.ontologymetrics

    registry = args.registry
    schema = json.load(args.schema)
    contact_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://obofoundry.org/config/registry_schema/contact",
        "title": "registry_schema",
        "properties": {

            "contact": schema['properties']['contact'],
        },
        "required": ["contact"],
        "level": "error"
    }
    license_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "http://obofoundry.org/config/registry_schema/license",
        "title": "registry_schema",
        "properties": {
            "license": schema['properties']['license'],
        },
        "required": ["license"],
        "level": "error"
    }
    robot_jar = args.robot_jar
    ro_file = args.relations
    profile = args.profile

    # Create the build directory for this ontology
    ontology_dir = args.outdir
    os.makedirs(ontology_dir, exist_ok=True)

    # Launch the JVM using the robot JAR
    py4j.java_gateway.launch_gateway(
        jarpath=robot_jar, classpath='org.obolibrary.robot.PythonOperation', die_on_exit=True, port=25333)

    # Activate gateway to JVM
    gateway = JavaGateway()

    try:
        robot_gateway = gateway.jvm.org.obolibrary.robot

        # IOHelper for working with ontologies
        io_helper = robot_gateway.IOHelper()

        # Handle ontology file
        big = namespace in BIG_ONTS

        # Load dashboard data if exists
        dashboard_yml = os.path.join(ontology_dir, "dashboard.yml")
        data_yml = dict()
        if os.path.isfile(dashboard_yml):
            with open(dashboard_yml, 'r') as f:
                data_yml = yaml.load(f, Loader=yaml.SafeLoader)

        if 'changed' not in data_yml or 'results' not in data_yml or data_yml['changed'] == True:
            print("Analysis has to be updated, running.")
        else:
            sys.exit(0)

        # Load raw ontology as OWLOntology object
        syntax = None
        if not metrics_file or not os.path.exists(metrics_file) or dash_utils.whitespace_only(metrics_file):
            # If ontology_file is None, the file does not exist, or the file is empty
            # Then the ontology is None
            syntax = None
        else:
            try:
                with open(metrics_file, 'r') as stream:
                    metrics_data = yaml.safe_load(stream)
                if metrics_data:
                    if 'metrics' in metrics_data and 'syntax' in metrics_data['metrics']:
                        syntax = metrics_data['metrics']['syntax']
            except Exception as e:
                print(f"ERROR: Unable to load {metrics_file}, cause: {e}.", flush=True)

        if not big:
            # Load ontology as OWLOntology object
            if not ontology_file or not os.path.exists(ontology_file) or dash_utils.whitespace_only(ontology_file):
                # If ontology_file is None, the file does not exist, or the file is empty
                # Then the ontology is None
                ont_or_file = None
            else:
                try:
                    ont_or_file = io_helper.loadOntology(ontology_file)
                except Exception:
                    print('ERROR: Unable to load \'{0}\''.format(ontology_file), flush=True)
                    ont_or_file = None
            # Get the Verison IRI
            version_iri = dash_utils.get_version_iri(ont_or_file)
        else:
            # Just provide path to file
            ont_or_file = ontology_file
            # Get the version IRI by text parsing
            version_iri = dash_utils.get_big_version_iri(ont_or_file)

        # Get the registry data
        yaml_data_raw = yaml.load(registry, Loader=yaml.SafeLoader)
        yaml_data = []
        for o in yaml_data_raw['ontologies']:
            yaml_data.append(yaml_data_raw['ontologies'][o])

        data = dash_utils.get_data(namespace, yaml_data)

        # Map of all ontologies to their domains
        domain_map = dash_utils.get_domains(yaml_data)
        # Map of RO labels to RO IRIs
        ro_props = fp_007.get_ro_properties(ro_file)

        if 'is_obsolete' in data and data['is_obsolete'] == 'true':
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
        
        for base_iri in data['base_ns']:
            logging.warning(f"Adding base IRI to IO Helper: {base_iri}.")
            io_helper.addBaseNamespace(base_iri)
        # This is added so the dashboard os not skippig checks on the ontology itself.
        io_helper.addBaseNamespace(f"http://purl.obolibrary.org/obo/{namespace}")
        
        if big:
            if namespace != 'gaz':
                # Report currently takes TOO LONG for GAZ
                print('Running ROBOT report on {0}...'.format(namespace), flush=True)
                report_obj = report_utils.BigReport(robot_gateway, namespace, ont_or_file, profile)
                report = report_obj.get_report()
                good_format = report_obj.get_good_format()
        else:
            if ont_or_file:
                # Ontology is not None
                print('Running ROBOT report on {0}...'.format(namespace), flush=True)
                report = report_utils.run_report(robot_gateway, io_helper, ont_or_file, profile)

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
            check_map[2] = fp_002.is_common_format(syntax)
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

        try:
            check_map[20] = fp_020.is_responsive(data)
        except Exception as e:
            check_map[20] = 'INFO|unable to run check 20'
            print('ERROR: unable to run check 20 for {0}\nCAUSE:\n{1}'.format(namespace, str(e)), flush=True)

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
        badge_message = []
        color = ""

        if err > 0:
            summary = 'ERROR'
            color = "red"
            summary_comment = '{0} errors'.format(err)
            badge_message.append(f"ERROR {err}")
        elif warn > 0:
            summary = 'WARN'
            color = "yellow"
            summary_comment = '{0} warnings'.format(warn)
        elif info > 0:
            summary = 'INFO'
            color = 'green'
            summary_comment = '{0} info messages'.format(info)
        else:
            summary = 'PASS'
            summary_comment = ''
            color = 'green'

        if warn > 0:
            badge_message.append(f"WARN {warn}")

        summary_count = dict()
        summary_count['ERROR'] = err
        summary_count['WARN'] = warn
        summary_count['INFO'] = info
        date = datetime.datetime.today()
        save_data = {'namespace': namespace, 'version': version_iri, 'date': date,
                     'summary': {'status': summary, 'comment': summary_comment, 'summary_count': summary_count}, 'results': all_checks}

        oboscore_weights = config.get_oboscore_weights()
        oboscore_maximpacts = config.get_oboscore_max_impact()

        for key in save_data:
            data_yml[key] = save_data[key]

        raw_dashboard_score = compute_dashboard_score_alt1(data_yml, oboscore_weights, oboscore_maximpacts)
        raw_dashboard_score = float(raw_dashboard_score) / float(100)
        obo_dashboard_score = round_float(float(raw_dashboard_score))
        data_yml['metrics']['Info: Experimental OBO score']['_dashboard'] = obo_dashboard_score
        oboscore = compute_obo_score(data_yml['metrics']['Info: Experimental OBO score']['_impact'],
                                     data_yml['metrics']['Info: Experimental OBO score']['_reuse'],
                                     data_yml['metrics']['Info: Experimental OBO score']['_dashboard'],
                                     data_yml['metrics']['Info: Experimental OBO score']['_impact_external'],
                                     oboscore_weights)

        data_yml['metrics']['Info: Experimental OBO score']['oboscore'] = round_float(oboscore['score'])
        data_yml['metrics']['Info: Experimental OBO score']['_formula'] = oboscore['formula']

        obo_dashboard_score_pc = round_float(float((obo_dashboard_score*100)))
        # Save to YAML file
        print('Saving results to {0}'.format(dashboard_yml))
        create_dashboard_qc_badge(color, ", ".join(badge_message), ontology_dir)
        create_dashboard_score_badge("blue", f"{obo_dashboard_score_pc} %", ontology_dir)

        with open(dashboard_yml, 'w+') as f:
            yaml.dump(data_yml, f)
    except Exception:
        logging.exception(f"Creating  dashboard for {ontology_file} failed")
    try:
        gateway.close()
    except Exception:
        pass

    sys.exit(0)

BIG_ONTS = []
#BIG_ONTS = ['bto', 'chebi', 'dron', 'gaz', 'ncbitaxon', 'ncit', 'pr', 'uberon']
OBO = 'http://purl.obolibrary.org/obo'

PRINCIPLE_MAP = {
    1: 'FP01 Open',
    2: 'FP02 Common Format',
    3: 'FP03 URIs',
    4: 'FP04 Versioning',
    5: 'FP05 Scope',
    6: 'FP06 Textual Definitions',
    7: 'FP07 Relations',
    8: 'FP08 Documented',
    9: 'FP09 Plurality of Users',
    11: 'FP11 Locus of Authority',
    12: 'FP12 Naming Conventions',
    16: 'FP16 Maintenance',
    20: 'FP20 Responsiveness'
}


if __name__ == '__main__':
    run()
