#!/usr/bin/env python3

import os
import yaml
import logging
import subprocess
import urllib.request
import hashlib
from subprocess import check_call
import requests
from pathlib import Path

def runcmd(cmd):
    logging.info("RUNNING: {}".format(cmd))
    p = subprocess.Popen([cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (out, err) = p.communicate()
    logging.info('OUT: {}'.format(out))
    if err:
        logging.error(err)
    if p.returncode != 0:
        raise Exception('Failed: {}'.format(cmd))


def read_txt_from_url_as_lines(url):
    profile_raw = urllib.request.urlopen(url).read()
    profile_lines = profile_raw.decode('utf-8').split('\n')
    return profile_lines


def open_yaml_from_url(url):
    raw = urllib.request.urlopen(url).read()
    return yaml.load(raw, Loader=yaml.SafeLoader)


class DashboardConfig:

    def __init__(self, config_file):
        self.config = yaml.load(open(config_file, 'r'))
        self.default_profile = "https://raw.githubusercontent.com/ontodev/robot/master/robot-core/src/main/resources" \
                               "/report_profile.txt "
        self.obo_registry = "https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/ontologies.yml"

    def get_title(self):
        if "title" in self.config:
            return self.config.get("title")
        else:
            return "OBO Dashboard"

    def get_oboscore_weights(self):
        weights = dict()
        weights['no_base'] = 5
        weights['overall_error'] = 1
        weights['overall_warning'] = 0.5
        weights['overall_info'] = 0.1
        weights['report_errors'] = 0.05
        weights['report_warning'] = 0.01
        weights['report_info'] = 0.005
        if 'obo_score_weights' in self.config:
            for weight in self.config['obo_score_weights']:
                if 'impact_factor' in self.config['obo_score_weights']:
                    weights[weight] = self.config['obo_score_weights']['impact_factor'][weight]
        return weights

    def get_oboscore_max_impact(self):
        weights = dict()
        weights['no_base'] = 5
        weights['overall_error'] = 20
        weights['overall_warning'] = 10
        weights['overall_info'] = 5
        weights['report_errors'] = 10
        weights['report_warning'] = 5
        weights['report_info'] = 2
        if 'obo_score_weights' in self.config:
            for weight in self.config['obo_score_weights']:
                if 'max_impact' in self.config['obo_score_weights']:
                    weights[weight] = self.config['obo_score_weights']['max_impact'][weight]
        return weights

    def get_description(self):
        if "description" in self.config:
            return self.config.get("description")
        else:
            return "No description provided."

    def get_report_truncation_limit(self):
        if "report_truncation_limit" in self.config:
            limit = self.config.get("report_truncation_limit")
            if is_number(limit):
                return limit
            else:
                logging.info("report_truncation_limit is not a valid number")
                return 0
        else:
            return 0

    def get_robot_additional_prefixes(self):
        if "robot_additional_prefixes" in self.config:
            return self.config.get("robot_additional_prefixes")
        else:
            return {}

    def get_environment_variables(self):
        if "environment" in self.config:
            return self.config.get("environment")
        else:
            return {}

    def get_redownload_after_hours(self):
        if "redownload_after_hours" in self.config:
            return self.config.get("redownload_after_hours")
        else:
            return 0

    def get_robot_opts(self):
        if "robot_opts" in self.config:
            return self.config.get("robot_opts")
        else:
            return ""

    def get_force_regenerate_dashboard_after_hours(self):
        if "force_regenerate_dashboard_after_hours" in self.config:
            return self.config.get("force_regenerate_dashboard_after_hours")
        else:
            return 0

    def get_ontologies(self):
        ontologies = dict()
        ont_conf = self.config.get("ontologies")

        if 'registry' in ont_conf:
            if ont_conf['registry'] and ont_conf['registry'] != 'None':
                base = open_yaml_from_url(ont_conf['registry'])
                for o in base['ontologies']:
                    ontology = dict()
                    if 'activity_status' in o:
                        if o['activity_status'] != 'active':
                            continue

                    oid = o['id']
                    if 'preferredPrefix' in o:
                        oid_cap = o['preferredPrefix']
                    else:
                        oid_cap = oid.upper()
                    ontology['id'] = oid

                    if 'base_ns' in o:
                        ontology['base_ns'] = o['base_ns']
                    else:
                        ontology['base_ns'] = [f'http://purl.obolibrary.org/obo/{oid_cap}_']

                    if self._get_prefer_base():
                        ourl = self.base_url_if_exists(oid)
                    else:
                        ourl = f"http://purl.obolibrary.org/obo/{oid}.owl"
                    ontology['mirror_from'] = ourl
                    ontologies[oid] = ontology
        if 'custom' in ont_conf:
            for o in ont_conf['custom']:
                ontology = dict()
                oid = o['id']
                if 'preferredPrefix' in o:
                    oid_cap = o['preferredPrefix']
                else:
                    oid_cap = oid.upper()
                ontology['id'] = oid
                if 'mirror_from' in o:
                    ourl = o['mirror_from']
                else:
                    if self._get_prefer_base():
                        ourl = self.base_url_if_exists(oid)
                    else:
                        ourl = f"http://purl.obolibrary.org/obo/{oid}.owl"
                ontology['mirror_from'] = ourl
                if 'base_ns' not in o:
                    ontology['base_ns'] = [f'http://purl.obolibrary.org/obo/{oid_cap}_']

                for key in o:
                    if key not in ontology:
                        ontology[key] = o[key]
                ontologies[oid] = ontology
        obo_registry_yaml = open_yaml_from_url(self.obo_registry)
        for oid in ontologies:
            for ontology in obo_registry_yaml['ontologies']:
                if oid == ontology['id']:
                    for key in ontology:
                        if key not in ontologies[oid]:
                            ontologies[oid][key] = ontology[key]
                            if key == "preferredPrefix":
                                oid_cap = ontology[key]
                                ontologies[oid]['base_ns'].append(f'http://purl.obolibrary.org/obo/{oid_cap}_')
                    break
        return {'ontologies': ontologies}

    def base_url_if_exists(self, oid):
        ourl = f"http://purl.obolibrary.org/obo/{oid}/{oid}-base.owl"
        try:
            ret = requests.head(ourl, allow_redirects=True)
            if ret.status_code != 200:
                ourl = f"http://purl.obolibrary.org/obo/{oid}.owl"
            else:
                i = 0
                for line in urllib.request.urlopen(ourl):
                    i = i + 1
                    if i > 3:
                        break
                    l = line.decode('utf-8')
                    if "ListBucketResult" in l:
                        ourl = f"http://purl.obolibrary.org/obo/{oid}.owl"

        except Exception:
            ourl = f"http://purl.obolibrary.org/obo/{oid}.owl"
        return ourl

    def get_profile(self):
        profile_lines = []
        if 'profile' in self.config:
            profileconf = self.config.get('profile')
            if 'baseprofile' in profileconf:
                profile_lines = read_txt_from_url_as_lines(profileconf['baseprofile'])
            if 'custom' in profileconf:
                for c in profileconf['custom']:
                    profile_lines.append(c)
        if not profile_lines:
            profile_lines = read_txt_from_url_as_lines(self.default_profile)
        else:
            mandatory_lines = ["duplicate_label", "missing_definition", "duplicate_label", "missing_ontology_license",
                               "multiple_definitions", "multiple_labels"]
            missing_lines = []
            for test in mandatory_lines:
                covered = False
                for line in profile_lines:
                    if test in line:
                        covered = True
                        break
                if not covered:
                    logging.info(f"The {test} check is required by the framework and cant be skipped. Adding...")
                    missing_lines.append(f"WARN\t{test}")
            profile_lines.extend(missing_lines)
        return profile_lines

    def _get_prefer_base(self):
        if "prefer_base" in self.config:
            return self.config.get("prefer_base")
        else:
            return False


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def sha256sum(filename):
    h  = hashlib.sha256()
    b  = bytearray(128*1024)
    mv = memoryview(b)
    with open(filename, 'rb', buffering=0) as f:
        for n in iter(lambda : f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()

def load_yaml(filepath):
    with open(filepath, 'r') as f:
        data = yaml.load(f, Loader=yaml.SafeLoader)
    return data


def robot_prepare_ontology(o_path, o_out_path, o_metrics_path, base_iris, robot_prefixes={}, robot_opts="-v"):
    logging.info(f"Preparing {o_path} for dashboard.")
    try:
        callstring = ['robot']
        callstring.extend(['metrics', robot_opts, '-i', o_path])
        for prefix in robot_prefixes:
            callstring.extend(['--prefix', f"{prefix}: {robot_prefixes[prefix]}"])
        callstring.extend(['--metrics', 'extended-reasoner','-f','yaml','-o',o_metrics_path, 'merge', 'remove'])
        #base_iris_string = " ".join([f"--base-iri \"{s}\"" for s in sbase_iris])
        for s in base_iris:
            callstring.extend(['--base-iri',s])
        callstring.extend(["--axioms", "external", "-p", "false"])
        callstring.extend(['--output', o_out_path])
        logging.info(callstring)
        check_call(callstring)
    except Exception as e:
        raise Exception(f"Preparing {o_path} for dashboard failed...", e)

def count_up(dictionary, value):
    if value not in dictionary:
        dictionary[value] = 0
    dictionary[value] = dictionary[value] + 1
    return dictionary


def save_yaml(dictionary, file_path):
    with open(file_path, 'w') as file:
        yaml.dump(dictionary, file)