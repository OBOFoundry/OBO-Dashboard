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


class Dashboard:
    def __init__(self, namespace, ontology, registry, license_schema, contact_schema, ro_file, outdir):
        """
        :param str namespace: namespace of ontology to check
        :param str ontology: path to ontology to check
        :param TextIOWrapper registry: file containing all registry YAML data
        :param JSON license_schema: JSON schema for license field
        :param JSON contact_schema: JSON schema for contact field
        :param TextIOWrapper ro_file: CSV file containing RO IRI and labels
        :param str outdir: path to output directory
        """
        self.namespace = namespace
        self.license = license_schema
        self.contact = contact_schema
        self.version_iri = None

        # Make sure master build dir exists
        self.ontology_dir = outdir
        os.makedirs(self.ontology_dir, exist_ok=True)

        # Launch the JVM using the robot JAR
        py4j.java_gateway.launch_gateway(
            jarpath='build/robot.jar', classpath='org.obolibrary.robot.PythonOperation', die_on_exit=True, port=25333)
        # Activate gateway to JVM
        self.gateway = JavaGateway()
        self.robot_gateway = self.gateway.jvm.org.obolibrary.robot
        # IOHelper for working with ontologies
        self.io_helper = self.robot_gateway.IOHelper()

        # Maybe run special "big" checks
        self.big = namespace in BIG_ONTS

        # Handle the ontology file itself
        if not self.big:
            # Load ontology object
            self.ont_or_file = self.load_ontology_from_file(ontology)
            self.version_iri = dash_utils.get_version_iri(self.ont_or_file)
        else:
            # Just provide path to file
            self.ont_or_file = ontology
            self.version_iri = dash_utils.get_big_version_iri(self.ont_or_file)

        # Get the registry data
        yaml_data = yaml.load(registry, Loader=yaml.SafeLoader)
        yaml_data = yaml_data['ontologies']
        self.data = get_data(self.namespace, yaml_data)

        # Get a map of each NS to its domain(s)
        self.domain_map = get_domains(yaml_data)

        # RO properties for relations check
        self.ro_props = fp_007.get_ro_properties(ro_file)

    def load_ontology_from_file(self, path):
        """Given a path to an ontology file, load the file as an OWLOntology.
        """
        if not path:
            return None
        try:
            ont = self.io_helper.loadOntology(path)
        except Exception:
            print('ERROR: Unable to load \'{0}\''.format(path), flush=True)
            return None
        return ont

    def load_ontology_from_iri(self, purl):
        """Given a PURL, return an OWLOntology object.
        """
        iri = self.gateway.jvm.org.semanticweb.owlapi.model.IRI.create(purl)
        try:
            ont = self.io_helper.loadOntology(iri)
        except Exception:
            print('ERROR: Unable to load <{0}>'.format(purl), flush=True)
            return None
        return ont

    def run_checks(self, ont_or_file, report, good_format):
        """
        :param ont_or_file:
        :param report:
        :param good_format:
        :return:
        """
        check_map = {}
        try:
            if self.big:
                check_map[1] = fp_001.big_is_open(ont_or_file, self.data, self.license)
            else:
                check_map[1] = fp_001.is_open(ont_or_file, self.data, self.license)
        except Exception as e:
            check_map[1] = 'INFO|unable to run check 1'
            print('ERROR: unable to run check 1 for {0}\nCAUSE:\n{1}'.format(self.namespace, str(e)), flush=True)

        try:
            if self.big:
                check_map[2] = fp_002.big_is_common_format(good_format)
            else:
                check_map[2] = fp_002.is_common_format(ont_or_file)
        except Exception as e:
            check_map[2] = 'INFO|unable to run check 2'
            print('ERROR: unable to run check 2 for {0}\nCAUSE:\n{1}'.format(self.namespace, str(e)), flush=True)

        try:
            if self.big:
                check_map[3] = fp_003.big_has_valid_uris(self.namespace, ont_or_file, self.ontology_dir)
            else:
                check_map[3] = fp_003.has_valid_uris(self.robot_gateway, self.namespace, ont_or_file, self.ontology_dir)
        except Exception as e:
            check_map[3] = 'INFO|unable to run check 3'
            print('ERROR: unable to run check 3 for {0}\nCAUSE:\n{1}'.format(self.namespace, str(e)), flush=True)

        try:
            if self.big:
                check_map[4] = fp_004.big_has_versioning(ont_or_file)
            else:
                check_map[4] = fp_004.has_versioning(ont_or_file)
        except Exception as e:
            check_map[4] = 'INFO|unable to run check 4'
            print('ERROR: unable to run check 4 for {0}\nCAUSE:\n{1}'.format(self.namespace, str(e)), flush=True)

        try:
            check_map[5] = fp_005.has_scope(self.data, self.domain_map)
        except Exception as e:
            check_map[5] = 'INFO|unable to run check 5'
            print('ERROR: unable to run check 5 for {0}\nCAUSE:\n{1}'.format(self.namespace, str(e)), flush=True)

        try:
            check_map[6] = fp_006.has_valid_definitions(report)
        except Exception as e:
            check_map[6] = 'INFO|unable to run check 6'
            print('ERROR: unable to run check 6 for {0}\nCAUSE:\n{1}'.format(self.namespace, str(e)), flush=True)

        try:
            if self.big:
                check_map[7] = fp_007.big_has_valid_relations(
                    self.namespace, ont_or_file, self.ro_props, self.ontology_dir)
            else:
                check_map[7] = fp_007.has_valid_relations(self.namespace, ont_or_file, self.ro_props, self.ontology_dir)
        except Exception as e:
            check_map[7] = 'INFO|unable to run check 7'
            print('ERROR: unable to run check 7 for {0}\nCAUSE:\n{1}'.format(self.namespace, str(e)), flush=True)

        try:
            check_map[8] = fp_008.has_documentation(self.data)
        except Exception as e:
            check_map[8] = 'INFO|unable to run check 8'
            print('ERROR: unable to run check 8 for {0}\nCAUSE:\n{1}'.format(self.namespace, str(e)), flush=True)

        try:
            check_map[9] = fp_009.has_users(self.data)
        except Exception as e:
            check_map[9] = 'INFO|unable to run check 9'
            print('ERROR: unable to run check 9 for {0}\nCAUSE:\n{1}'.format(self.namespace, str(e)), flush=True)

        try:
            check_map[11] = fp_011.has_contact(self.data, self.contact)
        except Exception as e:
            check_map[11] = 'INFO|unable to run check 11'
            print('ERROR: unable to run check 11 for {0}\nCAUSE:\n{1}'.format(self.namespace, str(e)), flush=True)

        try:
            check_map[12] = fp_012.has_valid_labels(report)
        except Exception as e:
            check_map[12] = 'INFO|unable to run check 12'
            print('ERROR: unable to run check 12 for {0}\nCAUSE:\n{1}'.format(self.namespace, str(e)), flush=True)

        try:
            if self.big:
                check_map[16] = fp_016.big_is_maintained(ont_or_file)
            else:
                check_map[16] = fp_016.is_maintained(ont_or_file)
        except Exception as e:
            check_map[16] = 'INFO|unable to run check 16'
            print('ERROR: unable to run check 16 for {0}\nCAUSE:\n{1}'.format(self.namespace, str(e)), flush=True)

        # finally, add the report results to the dashboard and save the report
        try:
            check_map['report'] = report_utils.process_report(self.robot_gateway, report, self.ontology_dir)
        except Exception as e:
            check_map['report'] = 'INFO|unable to save report'
            print('ERROR: unable to save ROBOT report for {0}\nCAUSE:\n{1}'.format(self.namespace, str(e)), flush=True)

        return check_map

    def big_check_principles(self, file):
        """
        :param file:
        :return:
        """
        report = None
        good_format = None
        if self.namespace != 'gaz':
            # Report currently takes TOO LONG for GAZ
            print('Running ROBOT report on {0}...'.format(self.namespace), flush=True)
            report_obj = report_utils.BigReport(self.robot_gateway, self.namespace, file)
            report = report_obj.get_report()
            good_format = report_obj.get_good_format()

        # run each principle check
        check_map = self.run_checks(file, report, good_format)

        # remove from memory
        if self.namespace != 'gaz':
            del report_obj
            del report

        return check_map

    def check_principles(self, ont):
        """
        :param ont:
        :return:
        """
        if ont:
            print('Running ROBOT report on {0}...'.format(self.namespace), flush=True)
            report = report_utils.run_report(self.robot_gateway, self.io_helper, ont)
        else:
            report = None

        # run each principle check
        check_map = self.run_checks(ont, report, None)

        # remove from memory
        del report
        del ont

        return check_map

    def exec_checks(self):
        """
        :return:
        """
        if 'is_obsolete' in self.data and self.data['is_obsolete'] is 'true':
            # do not run on obsolete ontologies
            print('{0} is obsolete and will not be checked...'.format(self.namespace), flush=True)
            gc.collect()
            sys.exit(0)
        try:
            print('-----------------\nChecking ' + self.namespace, flush=True)
            if self.big:
                return self.big_check_principles(self.ont_or_file)
            else:
                return self.check_principles(self.ont_or_file)
        except Exception as e:
            # Could not complete, exit with status 1
            print('ERROR: Unable to finish check on {0}\nCAUSE:\n{1}'.format(self.namespace, str(e)), flush=True)
            gc.collect()
            sys.exit(1)

    def save_results(self, check_map):
        """
        :param check_map:
        :return:
        """
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

        save_data = {'namespace': self.namespace, 'version': self.version_iri, 'date': date.strftime('%Y-%m-%d'),
                     'summary': {'status': summary, 'comment': summary_comment}, 'results': all_checks}

        outfile = '/'.join([self.ontology_dir, 'dashboard.yml'])
        print('Saving results to {0}'.format(outfile))

        with open(outfile, 'w+') as f:
            yaml.dump(save_data, f)

    def run(self):
        check_map = self.exec_checks()
        self.save_results(check_map)


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


# --- GLOBALS ---

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
    ns = os.path.splitext(owl)[0]

    db = Dashboard(
            ns,
            args.ontology,
            args.registry,
            json.load(args.license),
            json.load(args.contact),
            args.relations,
            args.outdir)
    db.run()
