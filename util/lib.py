#!/usr/bin/env python3

import hashlib
import json
import logging
import subprocess
import threading
import urllib.request
from datetime import datetime
from subprocess import check_call

import requests
import yaml
from requests.exceptions import ChunkedEncodingError

obo_purl = "http://purl.obolibrary.org/obo/"

class Command(object):
    def __init__(self, cmd):
        self.cmd = cmd
        self.process = None

    def run(self, timeout):
        def target():
            logging.info(f"RUNNING: {self.cmd} (Timeout: {timeout})")
            self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            (out, err) = self.process.communicate()
            logging.info('OUT: {}'.format(out))
            if err:
                logging.info('ERROR: {}'.format(err))

        thread = threading.Thread(target=target)
        thread.start()

        thread.join(timeout)
        if thread.is_alive():
            print('Terminating process')
            self.process.terminate()
            thread.join()
        if self.process.returncode != 0:
            raise Exception(f'Failed: {self.cmd} with return code {self.process.returncode}')


def runcmd(cmd, timeout=3600):
    command = Command(cmd)
    command.run(timeout=timeout)


def read_txt_from_url_as_lines(url):
    profile_raw = urllib.request.urlopen(url).read()
    profile_lines = profile_raw.decode('utf-8').split('\n')
    return profile_lines


def open_yaml_from_url(url):
    raw = urllib.request.urlopen(url).read()
    return yaml.load(raw, Loader=yaml.SafeLoader)


class DashboardConfig:

    def __init__(self, config_file):
        self.config = yaml.load(open(config_file, 'r'), Loader=yaml.SafeLoader)
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
        weights['impact_external'] = 3
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
        weights['impact_external'] = 3
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

    def get_dashboard_report_timeout_seconds(self):
        if "dashboard_report_timeout_seconds" in self.config:
            return self.config.get("dashboard_report_timeout_seconds")
        else:
            return 3600


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
        prefixes = {}
        ontologies = self.get_ontology_ids()

        for o in ontologies:
            prefixes[o.upper()+"ALT"] = f'http://purl.obolibrary.org/obo/{o}#'

        if "robot_additional_prefixes" in self.config:
            prefixes.update(self.config.get("robot_additional_prefixes"))

        return prefixes

    def get_environment_variables(self):
        if "environment" in self.config:
            return self.config.get("environment")
        else:
            return {}

    def is_skip_existing(self):
        if "skip_existing" in self.config:
            return self.config.get("skip_existing")
        else:
            return False

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

    def get_ontology_ids(self):
        ontologies = []
        ont_conf = self.config.get("ontologies")

        if 'registry' in ont_conf:
            if ont_conf['registry'] and ont_conf['registry'] != 'None':
                base = open_yaml_from_url(ont_conf['registry'])
                for o in base['ontologies']:
                    if 'activity_status' in o:
                        if o['activity_status'] != 'active':
                            continue

                    oid = o['id']
                    ontologies.append(oid)
        if 'custom' in ont_conf:
            for o in ont_conf['custom']:
                ontologies.append(o['id'])
        return list(set(ontologies))

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
                        ontology['base_ns'] = []
                        ontology['base_ns'].append(f'http://purl.obolibrary.org/obo/{oid_cap}_')
                        ontology['base_ns'].append(f'http://purl.obolibrary.org/obo/{oid}#')

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
                    ontology['base_ns'] = []
                    ontology['base_ns'].append(f'http://purl.obolibrary.org/obo/{oid_cap}_')
                    ontology['base_ns'].append(f'http://purl.obolibrary.org/obo/{oid}#')

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


def robot_prepare_ontology(o_path, o_out_path, o_metrics_path, base_iris, make_base, robot_prefixes={}, robot_opts="-v"):
    logging.info(f"Preparing {o_path} for dashboard.")
    
    callstring = ['robot', 'merge', '-i', o_path]
    
    if robot_opts:
        callstring.append(f"{robot_opts}")
    
    ### Measure stuff
    callstring.extend(['measure'])
    for prefix in robot_prefixes:
        callstring.extend(['--prefix', f"{prefix}: {robot_prefixes[prefix]}"])
    callstring.extend(['--metrics', 'extended-reasoner','-f','yaml','-o',o_metrics_path])
    
    ## Extract base
    if make_base:
        callstring.extend(['remove'])
        for s in base_iris:
            callstring.extend(['--base-iri',s])
        callstring.extend(["--axioms", "external", "--trim", "false", "-p", "false"])
    
    ### Measure stuff on base
    callstring.extend(['measure'])
    for prefix in robot_prefixes:
        callstring.extend(['--prefix', f"{prefix}: {robot_prefixes[prefix]}"])
    callstring.extend(['--metrics', 'extended-reasoner','-f','yaml','-o',f"{o_metrics_path}.base.yml"])
    
    ## Output
    callstring.extend(['merge', '--output', o_out_path])
    logging.info(callstring)
    
    try:
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


def save_json(dictionary, file_path):
    def datetime_serializer(o):
        if isinstance(o, datetime):
            return o.isoformat()
        raise TypeError("Type not serializable")

    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(dictionary, file, default=datetime_serializer, indent=2)


def get_hours_since(timestamp):
    modified_date = datetime.fromtimestamp(timestamp)
    now = datetime.now()
    duration = now - modified_date
    hours_since = (duration.total_seconds() // 3600)
    return hours_since

def compute_obo_score(impact, reuse, dashboard, impact_external, weights):
    impact_weight = weights['impact']
    reuse_weight = weights['reuse']
    dashboard_weight = weights['dashboard']
    impact_external_weight = weights['impact_external']
    #sum_weights = impact_weight + reuse_weight + dashboard_weight + impact_external_weight
    #score_sum = sum([impact_weight * impact, reuse_weight * reuse, dashboard_weight * dashboard,
    #                 impact_external_weight * impact_external])
    #formula = f"({impact_weight}*impact+{dashboard_weight}*dashboard+{reuse_weight}*reuse+{impact_external_weight}*impact_external)/{sum_weights}"

    sum_weights = impact_weight+dashboard_weight
    score_sum = sum([impact_weight*impact, dashboard_weight*dashboard])
    formula = f"({impact_weight}*impact+{dashboard_weight}*dashboard)/{sum_weights}"
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
        no_base = weights['no_base']

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

def compute_dashboard_score_alt1(data, weights, maximpacts):
    """Computing dashboard score based purely on the number of failed categories"""

    if 'failure' in data:
        return 0

    score = 100

    if 'results' in data:
        ct_categories = len(data['results']) + 1 # The + 1 is the requirement of having a base.
        weight_per_category = float((100 / ct_categories))
        for cat in data['results']:
            if 'status' in data['results'][cat]:
                if data['results'][cat]['status'] == 'ERROR':
                    score -= weight_per_category
                elif data['results'][cat]['status'] == 'WARN':
                    score -= (weight_per_category/3)
                elif data['results'][cat]['status'] == 'INFO':
                    score -= (weight_per_category / 10)
                elif data['results'][cat]['status'] == 'PASS':
                    score -= 0
                else:
                    logging.warning(f"compute_dashboard_score_alt1(): Results section exists but unrecognised status {data['results'][cat]['status']}.")
                    return 0
            else:
                logging.warning(
                    f"compute_dashboard_score_alt1(): Results section exists but no status entry for {cat}.")
                return 0
    else:
        return 0

    if 'base_generated' in data and data['base_generated'] == True:
        score -= weight_per_category

    if score < 0:
        score = 0

    return "%.2f" % score

def round_float(n):
    strfloat = "%.3f" % n
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
    if ns.startswith(obo_purl) and ns.endswith("_"):
        ns = ns.replace(obo_purl,"")
        ns = ns[:-1]
        return ns
    msg = f"Namespace {ns} not found in curie map, aborting.."
    raise Exception(msg)

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
    return float(score_string)

def create_dashboard_qc_badge(color: str, message: str, outdir: str):
    create_badge(color, message, "QC", f"{outdir}/dashboard-qc-badge.json")


def create_dashboard_score_badge(color: str, message: str, outdir: str):
    create_badge(color, message, "OBO Dashboard Score", f"{outdir}/dashboard-score-badge.json")


def create_badge(color: str, message: str, label:str, filepath: str):
    odk_svg='<svg id="Layer_1" data-name="Layer 1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 135.54 133.3"><defs><style>.cls-1{fill:#fff;}.cls-2{fill:#231f20;}</style></defs><path class="cls-1" d="M85.31,20.58l-4-16.64s0,0,0,0c-1.11-.14-2.21-.26-3.33-.35s-2.24-.15-3.36-.18-2.26,0-3.4,0c-.82,0-1.66.06-2.49.11L63.21,19.66c-.22,0-.43.11-.65.15l0,.11c-1.58.3-3.13.68-4.65,1.12s-3,1-4.45,1.53L40.52,11.64c-.58.32-1.17.63-1.74,1-1,.56-1.91,1.14-2.83,1.74s-1.84,1.23-2.73,1.88-1.77,1.31-2.63,2l-.73.6L34.72,35c-.15.16-.28.33-.42.48v0c-1.12,1.18-2.17,2.42-3.17,3.7s-1.95,2.59-2.84,4h-.06v0l-16.83-1c-.31.62-.62,1.23-.91,1.85-.46,1-.88,2-1.29,3.07-.28.69-.53,1.39-.79,2.09-.12.35-.26.7-.38,1.05-.36,1-.69,2.1-1,3.17-.1.33-.17.68-.26,1l13.4,10.13a54.29,54.29,0,0,0-.56,10.73L5.25,84.54c.09.52.16,1,.26,1.55.21,1.08.44,2.16.7,3.23s.54,2.14.85,3.2.65,2.12,1,3.16c.14.42.31.82.46,1.24h0L25.22,97l0,0h.13a51.6,51.6,0,0,0,5.88,9L24.87,122c.61.59,1.21,1.18,1.83,1.74.85.76,1.71,1.49,2.59,2.2S31.06,127.35,32,128s1.62,1.14,2.45,1.69l13.68-9.92c.14.07.3.12.43.19l.1-.07c1.22.59,2.47,1.11,3.73,1.59a19.94,19.94,0,0,1,9.28-28.87A22.89,22.89,0,0,1,72.29,49.46a23.11,23.11,0,0,1,6,.82,19.92,19.92,0,0,1,11.53-27.8l.16-.42A47.65,47.65,0,0,0,85.31,20.58Z"/><path class="cls-2" d="M43.71,37.89V34.77c0-2.89,1.57-4,4.09-4s4.09,1.07,4.09,4v3.12c0,3-1.2,4.17-4.09,4.17S43.71,40.86,43.71,37.89Zm6.4,0V34.77c0-2-.84-2.37-2.31-2.37s-2.32.39-2.32,2.37v3.12c0,2,.73,2.62,2.32,2.62S50.11,39.87,50.11,37.89Z"/><path class="cls-2" d="M60.46,41.87l-.22-1.44a2.71,2.71,0,0,1-2.71,1.5c-2.19,0-3.7-1-3.7-3.94V35.11c0-3,1.4-4.24,3.7-4.24a3,3,0,0,1,2.63.95V27.27H62v14.6Zm-2.54-9.28c-1.59,0-2.31.63-2.31,2.56V38c0,1.79.72,2.26,2.18,2.26s2.37-.71,2.37-2.86V35.05C60.16,33.19,59.51,32.59,57.92,32.59Z"/><path class="cls-2" d="M67,37h-.8v4.85H64.42V27.45H66.2v7.88h.71L70.29,31h2.17l-4,5.13,4.37,5.79H70.7Z"/><path class="cls-1" d="M126.8,64.76a4.35,4.35,0,0,0-3.28,1.52l-6.24-3A8.16,8.16,0,0,0,115.15,55l3.73-5.15a2.7,2.7,0,0,0,.63.07A2.93,2.93,0,1,0,116.58,47a2.87,2.87,0,0,0,.42,1.48l-3.74,5.15a8.21,8.21,0,0,0-12,7.27,7.59,7.59,0,0,0,.11,1.27L84.84,67.27a13.6,13.6,0,0,0-3.38-4.87l10.7-13.85a8.12,8.12,0,0,0,4,1.07,8.24,8.24,0,1,0-5.89-2.5L79.61,61a13.54,13.54,0,1,0-9.5,24.75l-1.3,17.14a8.21,8.21,0,0,0,.55,16.4l.49,0,1.38,6.7a2.3,2.3,0,1,0,2.29-.46l-1.38-6.7a8.21,8.21,0,0,0-1-15.74l1.3-17.13a13.5,13.5,0,0,0,6.26-1.6l8.18,12.51A8.2,8.2,0,0,0,90.48,111L90,116.62a4.39,4.39,0,1,0,2.33.2l.47-5.66A8.21,8.21,0,0,0,99.49,107l7.1,2.71a2.32,2.32,0,1,0,.84-2.18l-7.11-2.71a8.2,8.2,0,0,0-11.48-9.24L80.65,83a13.74,13.74,0,0,0,3.81-4.71L99.14,84a8,8,0,0,0-.22,1.84,8.22,8.22,0,1,0,1-4L85.3,76.12a13.36,13.36,0,0,0,.23-6.62L102,64.42a8.21,8.21,0,0,0,14.27,1l6.24,3a4.41,4.41,0,0,0-.08.73,4.36,4.36,0,1,0,4.36-4.36Z"/></svg>'
    json_data = {
        "schemaVersion": 1,
        "label": f"{label}",
        "message": f"{message}",
        "color": f"{color}",
        "logoSvg": odk_svg
    }
    json_string = json.dumps(json_data)
    with open(filepath, "w") as text_file:
        print(json_string, file=text_file)

def url_exists(url: str) -> bool:
    # check the URL resolves, but don't download it in full
    # inspired by https://stackoverflow.com/a/69016995/802504 
    # more updated solution
    try:
        with requests.head(url, allow_redirects=True) as res:
            return (res.status_code == 200)
    except Exception as e:
        # Any errors with connection will be considered
        # as the URL not existing
        logging.error(e, exc_info=True)
    return False


def download_file(url, dest_path, retries=3):
    """
    Download the ontology from the URL to a local path. Retries on ChunkedEncodingError.
    """
    attempt = 0
    while attempt < retries:
        try:
            response = requests.get(url, stream=True, timeout=1000000)
            response.raise_for_status()

            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=32768):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)
            logging.info("Downloaded %s to %s", url, dest_path)
            return  # Exit the function if download is successful
        except ChunkedEncodingError as e:
            attempt += 1
            logging.warning("ChunkedEncodingError encountered: %s. Retrying %s/%s...", e, attempt, retries)
        except Exception as e:
            logging.exception("Failed to download %s: %s", url, e)
