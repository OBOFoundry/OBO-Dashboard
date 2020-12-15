#!/usr/bin/env python3

import yaml
import logging
import subprocess
import urllib.request
import hashlib
from subprocess import check_call
import requests
from datetime import datetime

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
        weights['dashboard'] = 2
        weights['impact'] = 3
        weights['reuse'] = 1
        if 'obo_score_weights' in self.config:
            for weight in self.config['obo_score_weights']:
                if 'impact_factor' in self.config['obo_score_weights'][weight]:
                    weights[weight] = self.config['obo_score_weights'][weight]['impact_factor']
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
        weights['dashboard'] = 2
        weights['impact'] = 3
        weights['reuse'] = 1
        if 'obo_score_weights' in self.config:
            for weight in self.config['obo_score_weights']:
                if 'max_impact' in self.config['obo_score_weights'][weight]:
                    weights[weight] = self.config['obo_score_weights'][weight]['max_impact']
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
        callstring.extend(['measure', robot_opts, '-i', o_path])
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



def get_hours_since(timestamp):
    modified_date = datetime.fromtimestamp(timestamp)
    now = datetime.now()
    duration = now - modified_date
    hours_since = (duration.total_seconds() // 3600)
    return hours_since

def compute_obo_score(impact, reuse, dashboard, weights):
    impact_weight = weights['impact']
    reuse_weight = weights['reuse']
    dashboard_weight = weights['dashboard']
    sum_weights = impact_weight+reuse_weight+dashboard_weight
    score_sum = sum([impact_weight*impact, reuse_weight*reuse, dashboard_weight*dashboard])
    formula = f"({impact_weight}*impact+{dashboard_weight}*dashboard+{reuse_weight}*reuse)/{sum_weights}"
    score = score_sum/sum_weights
    return { "score": score, "formula" : formula }


def compute_dashboard_score(data, weights, maximpacts):

    if 'failure' in data:
        return 0

    oboscore = 100
    no_base = 0
    report_errors = 0
    report_warning = 0
    report_info = 0

    overall_error = 0
    overall_warning = 0
    overall_info = 0

    if 'base_generated' in data and data['base_generated'] == True:
        no_base = weights['base_generated']

    if 'results' in data:
        if 'ROBOT Report' in data['results']:
            if 'results' in data['results']['ROBOT Report']:
                report_errors = data['results']['ROBOT Report']['results']['ERROR']
                report_warning = data['results']['ROBOT Report']['results']['WARN']
                report_info = data['results']['ROBOT Report']['results']['INFO']

    if 'summary' in data:
        overall_error = data['summary']['summary_count']['ERROR']
        overall_warning = data['summary']['summary_count']['WARN']
        overall_info = data['summary']['summary_count']['INFO']

    oboscore = oboscore - score_max(weights['no_base'] * no_base, maximpacts['no_base'])
    oboscore = oboscore - score_max(weights['overall_error'] * overall_error, maximpacts['overall_error'])
    oboscore = oboscore - score_max(weights['overall_warning'] * overall_warning, maximpacts['overall_warning'])
    oboscore = oboscore - score_max(weights['overall_info'] * overall_info, maximpacts['overall_info'])
    oboscore = oboscore - score_max(weights['report_errors'] * report_errors, maximpacts['report_errors'])
    oboscore = oboscore - score_max(weights['report_warning'] * report_warning, maximpacts['report_warning'])
    oboscore = oboscore - score_max(weights['report_info'] * report_info, maximpacts['report_info'])
    return "%.2f" % oboscore


def round_float(n):
    strfloat = "%.2f" % n
    return (float(strfloat))

def score_max(score,maxscore):
    if score > maxscore:
        return maxscore
    else:
        return score

def get_prefix_from_url_namespace(ns, curie_map):
    for prefix in curie_map:
        if ns==curie_map[prefix]:
            return prefix
    raise Exception(f"Namespace {ns} not found in curie map, aborting..")

def get_base_prefixes(curie_map, base_namespaces):
    internal_ns = []
    for ns in base_namespaces:
        prefix = get_prefix_from_url_namespace(ns, curie_map)
        internal_ns.append(prefix)
    return internal_ns

def compute_percentage_reused_entities(entity_use_map, internal_ns):
    internal_entities = 0
    external_entities = 0
    for prefix in entity_use_map:
        if prefix in internal_ns:
            internal_entities += entity_use_map[prefix]
        else:
            external_entities += entity_use_map[prefix]

    reuse_score = 100*(external_entities/(external_entities+internal_entities))
    score_string = "%.2f" % round(reuse_score, 2)
    return score_string
