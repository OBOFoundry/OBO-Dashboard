#!/usr/bin/env python3

import os
import yaml
import click
import logging
import urllib.request
import json


from lib import DashboardConfig, runcmd, sha256sum, save_yaml, \
    load_yaml, robot_prepare_ontology, get_hours_since, get_base_prefixes, \
    compute_percentage_reused_entities, round_float, create_dashboard_score_badge, \
    create_dashboard_qc_badge

logging.basicConfig(level=logging.INFO)

@click.group()
def cli():
    pass


@cli.command()
@click.option('-C', '--configfile', type=click.Path(exists=True),
              help="""
                path to a YAML configuration.
                See examples folder for examples.
                This is optional, configuration can also be passed
                by command line, but an explicit config file is preferred.
                """)
@click.option('-d', '--clean/--no-clean', default=False,
              help="""
                Delete the contents of the current dashboard dir prior to processing.
                """)
def rundashboard(configfile, clean):
    config = DashboardConfig(configfile)
    profile = config.get_profile()
    ontologies = config.get_ontologies()
    with open('profile.txt', 'w') as f:
        for item in profile:
            if item:
                f.write("%s\n" % item)
    dependencies_path = os.path.join('dependencies')

    if not os.path.isdir(dependencies_path):
        os.mkdir(dependencies_path)

    ontologies_path = os.path.join(dependencies_path, 'ontologies.yml')
    with open(ontologies_path, 'w') as file:
        yaml.dump(ontologies, file)

    environment_variables = config.get_environment_variables()
    make_parameters = ""
    for envi in environment_variables:
        val = environment_variables[envi]
        logging.info(f"Setting environment variable {envi}={val}")
        os.environ[envi] = val
        make_parameters += f"{envi}={val} "

    if clean:
        runcmd(f"make clean {make_parameters} -B", config.get_dashboard_report_timeout_seconds())

    logging.info("Prepare ontologies")
    build_dir = os.path.join("build")
    ontology_dir = os.path.join(build_dir, "ontologies")
    dashboard_dir = os.path.join("dashboard")

    if not os.path.isdir(build_dir):
        os.mkdir(build_dir)
    if not os.path.isdir(ontology_dir):
        os.mkdir(ontology_dir)
    if not os.path.isdir(dashboard_dir):
        os.mkdir(dashboard_dir)

    prepare_ontologies(ontologies['ontologies'], ontology_dir, dashboard_dir, make_parameters, config)
    logging.info("Building the dashboard")
    runcmd(f"make dashboard {make_parameters} -B", config.get_dashboard_report_timeout_seconds())
    logging.info("Postprocess files for github")
    runcmd(f"make truncate_reports_for_github {make_parameters} -B", config.get_dashboard_report_timeout_seconds())

info_usage_namespace = 'Info: Usage of namespaces in axioms'

errors={
    'corrupted_results_file': '',
    'missing_url': '',
    'missing_base_namespaces': '',
    'failed_download': '',
    'failed_sha256_hash': '',
    'no_sha256_hash': '',
    'not_an_ontology': '',
    'failed_robot_base': '',
    'missing_metrics_file': '',
    'empty_ontology': '',
    'inconsistent_ontology': '',
    'metrics_check_failed': '',
    'broken_metrics_file': '',
    'failed_ontology_dashboard': ''
}


def compute_external_impact(number_uses):
    try:
        number_uses = int(number_uses)
        if number_uses > 10:
            return 1
        elif number_uses > 5:
            return 0.75
        elif number_uses > 2:
            return 0.5
        elif number_uses >= 1:
            return 0.25
        else:
            return 0
    except:
        logging.warning(f'The variable {number_uses} is not a valid number of uses')
    return 0



def prepare_ontologies(ontologies, ontology_dir, dashboard_dir, make_parameters, config):
    ontologies_results = {}

    for o in ontologies:
        logging.info(f"Preparing {o}...")
        ont_path = os.path.join(ontology_dir, f"{o}-raw.owl")
        ont_base_path = os.path.join(ontology_dir, f"{o}.owl")
        ont_metrics_path = os.path.join(ontology_dir, f"{o}-metrics.yml")
        ont_dashboard_dir = os.path.join(dashboard_dir, o)
        ont_results_path = os.path.join(ont_dashboard_dir, "dashboard.yml")

        if not os.path.exists(ont_dashboard_dir):
            os.mkdir(ont_dashboard_dir)

        download = True
        make_base = True

        ont_results = dict()
        if os.path.exists(ont_results_path):

            try:
                ont_results = load_yaml(ont_results_path)
            except Exception:
                logging.exception(f'Corrupted results file for {o}: {ont_results_path}')
                ont_results['failure'] = 'corrupted_results_file'
                save_yaml(ont_results, ont_results_path)
                create_dashboard_qc_badge("red", "Corrupted results file", ont_dashboard_dir)
                create_dashboard_score_badge("lightgrey", "NA", ont_dashboard_dir)
                continue

        if config.is_skip_existing():
            ontologies_results[o] = ont_results
            logging.warning(
                f"Config is set to skipping, and {ont_results_path} exists, so dashboard HTML generation is entirely skipped for {o}")
            continue

        ont_results['namespace'] = o

        # If the ontology was downloaded recently (according to the setting)
        # Do not download it again.
        if os.path.isfile(ont_base_path):
            modified_timestamp = os.path.getmtime(ont_base_path)
            hours_since = get_hours_since(modified_timestamp)
            if hours_since < config.get_redownload_after_hours():
                logging.info(f"File has only been processed recently ({hours_since} hours ago), skipping {o}. "
                             f"Redownloading after {config.get_redownload_after_hours()} hours..")
                download = False

        # Get download URL
        try:
            ourl = ontologies[o]['mirror_from']
            if f'{o}-base.' in ourl:
                make_base = False
        except Exception:
            logging.exception(f'Missing download url for {o} in registry..')
            ont_results['failure'] = 'missing_url'
            save_yaml(ont_results, ont_results_path)
            create_dashboard_qc_badge("red", "Missing URL", ont_dashboard_dir)
            create_dashboard_score_badge("lightgrey", "NA", ont_dashboard_dir)
            continue

        # Get base namespaces
        try:
            base_namespaces = ontologies[o]['base_ns']
        except Exception:
            logging.exception(f'Missing base namespaces for {o} in registry..')
            ont_results['failure'] = 'missing_base_namespaces'
            save_yaml(ont_results, ont_results_path)
            create_dashboard_qc_badge("red", "Missing base namespaces", ont_dashboard_dir)
            create_dashboard_score_badge("lightgrey", "NA", ont_dashboard_dir)
            continue

        if download:
            logging.info(f"Downloading {o}...")
            try:
                urllib.request.urlretrieve(ourl, ont_path)
            except Exception:
                logging.exception(f'Failed to download {o} from {ourl}')
                ont_results['failure'] = 'failed_download'
                save_yaml(ont_results, ont_results_path)
                create_dashboard_qc_badge("red", "Failed to download", ont_dashboard_dir)
                create_dashboard_score_badge("lightgrey", "NA", ont_dashboard_dir)
                continue
        else:
            logging.info(f"Downloading {o} skipped.")

        # Determine hashcode of downloaded file, if either a new file was downloaded, or there is no hash from a
        # previous result. By default, we assume the file has changed; if there was a previously generated hashcode
        # and the hashcode is the same as the hashcode of the new file, we then assume it has not changed.
        ont_results['changed'] = download
        try:
            sha256_hash = sha256sum(ont_path)
            if 'sha256_hash' in ont_results:
                if ont_results['sha256_hash'] == sha256_hash:
                    modified_timestamp = os.path.getmtime(ont_path)
                    hours_since = get_hours_since(modified_timestamp)
                    if hours_since >= config.get_force_regenerate_dashboard_after_hours():
                        logging.info(f"{o} has been processed a while ago ({hours_since} hours ago). "
                                     f"Forcing dashboard generation..")
                    else:
                        logging.info(
                            f"The downloaded file for {o} is the same as the one used for a previous run "
                            f"(less than {config.get_force_regenerate_dashboard_after_hours()} hours ago). "
                            f"Skipping..")
                        ont_results['changed'] = False
                else:
                    logging.info(f"Hashcode for downloaded file is different, . "
                                 f"Forcing dashboard generation..")
            # Setting the new hashcode
            ont_results['sha256_hash'] = sha256_hash
        except Exception:
            logging.exception(f'Failed to compute hashcode of {o}.')
            ont_results['failure'] = 'failed_sha256_hash'
            save_yaml(ont_results, ont_results_path)
            create_dashboard_qc_badge("red", "Failed to compute hashcode", ont_dashboard_dir)
            create_dashboard_score_badge("lightgrey", "NA", ont_dashboard_dir)
            continue


        # If the files was previously processed, but there was a failure, we get rid of the error message
        # to try again. I cant think of a way that could happen, just playing it safe.
        if ont_results.get('sha256_hash'):
            ont_results.pop('failure', None)
        else:
            logging.exception(f'No hashcode for {ont_path}, aborting.')
            ont_results['failure'] = 'no_sha256_hash'
            save_yaml(ont_results, ont_results_path)
            create_dashboard_qc_badge("red", "No hashcode for file", ont_dashboard_dir)
            create_dashboard_score_badge("lightgrey", "NA", ont_dashboard_dir)
            continue

        ont_results['base_generated'] = make_base
        ont_results['mirror_from'] = ourl

        # Only if the downloaded file changed, run the rest of the code.
        if ont_results['changed'] == True or not os.path.isfile(ont_metrics_path) or not os.path.isfile(ont_base_path):

            logging.info(f"Verifyig downloaded file...")

            # Verification: ontology has at least 10 rows and does not contain the ListBucketResult string, which is
            # an indication that the purl is not configured correctly.
            try:
                with open(ont_path) as myfile:
                    head = [next(myfile) for x in range(10)]
                    for line in head:
                        if 'ListBucketResult' in line:
                            raise Exception("BBOP file, not url.. skipping.")
            except Exception:
                logging.error(f'Failed to verify {o} as downloaded from {ourl}')
                ont_results['failure'] = 'not_an_ontology'
                save_yaml(ont_results, ont_results_path)
                create_dashboard_qc_badge("red", "Not an ontology", ont_dashboard_dir)
                create_dashboard_score_badge("lightgrey", "NA", ont_dashboard_dir)
                continue

            logging.info(f"Creating basefile for {o}...")

            try:
                robot_prepare_ontology(ont_path, ont_base_path, ont_metrics_path, base_namespaces, make_base=make_base, robot_prefixes=config.get_robot_additional_prefixes(), robot_opts=config.get_robot_opts())
            except Exception:
                logging.exception(f'Failed to compute base file for {o}.')
                ont_results['failure'] = 'failed_robot_base'
                save_yaml(ont_results, ont_results_path)
                create_dashboard_qc_badge("red", "Failed to compute base", ont_dashboard_dir)
                create_dashboard_score_badge("lightgrey", "NA", ont_dashboard_dir)
                continue



        else:
            logging.info(f"{o} has not changed since last run, skipping process.")

        # Processing metrics
        if os.path.exists(ont_metrics_path):
            try:
                metrics = load_yaml(ont_metrics_path)
                curie_map = config.get_robot_additional_prefixes()
                curie_map.update(metrics['metrics']['curie_map'])
                base_prefixes = get_base_prefixes(curie_map, base_namespaces)
                ont_results['base_prefixes'] = base_prefixes
                ont_results['metrics'] = {}
                ont_results['metrics']['Info: Logical consistency'] = metrics['metrics']['consistent']
                ont_results['metrics']['Entities: Number of unsatisfiable classes'] = metrics['metrics'][
                    'unsatisfiable_class_count']
                ont_results['metrics']['Axioms: Number of axioms'] = metrics['metrics']['axiom_count_incl']
                ont_results['metrics']['Entities: Number of classes'] = metrics['metrics']['class_count_incl']
                ont_results['metrics']['Entities: Number of object properties'] = metrics['metrics'][
                    'obj_property_count_incl']
                ont_results['metrics']['Entities: % of entities reused'] = compute_percentage_reused_entities(
                    metrics['metrics']['namespace_entity_count_incl'], base_prefixes)
                ont_results['metrics'][info_usage_namespace] = metrics['metrics'][
                    'namespace_axiom_count_incl']
                ont_results['metrics']['Entities: Number of individuals'] = metrics['metrics'][
                    'individual_count_incl']
                ont_results['metrics']['Entities: Number of data properties'] = metrics['metrics'][
                    'dataproperty_count_incl']
                ont_results['metrics']['Entities: Number of annotation properties'] = metrics['metrics'][
                    'annotation_property_count_incl']
                ont_results['metrics']['Axioms: Breakdown of axiom types'] = metrics['metrics'][
                    'axiom_type_count_incl']
                ont_results['metrics']['Info: Breakdown of OWL class expressions used'] = metrics['metrics'][
                    'class_expression_count_incl']
                ont_results['metrics']['Info: Does the ontology fall under OWL 2 DL?'] = metrics['metrics'][
                    'owl2_dl']
                ont_results['metrics']['Info: How many externally documented uses?'] = len(ontologies[o]['usages']) if 'usages' in ontologies[o] else 0
                ont_results['metrics']['Info: Syntax'] = metrics['metrics']['syntax']
            except Exception:
                logging.exception(f'Broken metrics file for {o}: {ont_metrics_path}')
                ont_results['failure'] = 'broken_metrics_file'
                save_yaml(ont_results, ont_results_path)
                create_dashboard_qc_badge("red", "Failed metrics", ont_dashboard_dir)
                create_dashboard_score_badge("lightgrey", "NA", ont_dashboard_dir)
                continue
        else:
            logging.exception(f'Missing metrics file for {o}: {ont_metrics_path}')
            ont_results['failure'] = 'missing_metrics_file'
            create_dashboard_qc_badge("red", "Missing metrics", ont_dashboard_dir)
            create_dashboard_score_badge("lightgrey", "NA", ont_dashboard_dir)
            save_yaml(ont_results, ont_results_path)
            continue

        #### Check that the ontology has at least 1 axiom and is logically consistent
        try:
            if ont_results['metrics']['Axioms: Number of axioms'] < 1:
                logging.exception(f'Ontology has lass than one axiom: {o}')
                ont_results['failure'] = 'empty_ontology'
                create_dashboard_qc_badge("red", "Empty ontology", ont_dashboard_dir)
                create_dashboard_score_badge("lightgrey", "NA", ont_dashboard_dir)
                save_yaml(ont_results, ont_results_path)
                continue

            if not ont_results['metrics']['Info: Logical consistency']:
                logging.exception(f'Ontology is inconsistent: {o}')
                ont_results['failure'] = 'inconsistent_ontology'
                save_yaml(ont_results, ont_results_path)
                create_dashboard_qc_badge("red", "Inconsistent ontology", ont_dashboard_dir)
                create_dashboard_score_badge("lightgrey", "NA", ont_dashboard_dir)
                continue
        except Exception:
            logging.exception(f'Metrics based checks failed for {o}: {ont_metrics_path}')
            ont_results['failure'] = 'metrics_check_failed'
            save_yaml(ont_results, ont_results_path)
            create_dashboard_qc_badge("red", "Processing error: failed metrics", ont_dashboard_dir)
            create_dashboard_score_badge("lightgrey", "NA", ont_dashboard_dir)
            continue

        logging.info(f"{o}: preprocessing successful.")
        ontologies_results[o] = ont_results

    # This has to be done after all ontologies are analysed, because we need their usage information to quantify impact.

    logging.info(f"Computing cross-OBO usage metrics...")
    ontology_use = {}
    ontology_base_prefixes = {}
    for o in ontologies_results:
        if 'base_prefixes' in ontologies_results[o]:
            for prefix in ontologies_results[o]['base_prefixes']:
                ontology_base_prefixes[prefix] = o

    for o in ontologies_results:
        ont_results = ontologies_results[o]
        if 'metrics' in ont_results and \
                info_usage_namespace in ont_results['metrics'] and \
                'base_prefixes' in ont_results:

            for used_prefix in ont_results['metrics'][info_usage_namespace]:
                if used_prefix in ontology_base_prefixes:
                    ont_used_prefix = ontology_base_prefixes[used_prefix]
                    if ont_used_prefix not in ontology_use:
                        ontology_use[ont_used_prefix] = []
                    ontology_use[ont_used_prefix].append(o)

    logging.info(f"Build dashboard dependencies")
    runcmd(f"make  {make_parameters} dependencies/ontologies.yml dependencies/registry_schema.json build/ro-properties.csv profile.txt dashboard-config.yml", config.get_dashboard_report_timeout_seconds())

    logging.info(f"Computing obo score and generating individual dashboard files...")
    for o in ontologies_results:
        ont_dashboard_dir = os.path.join(dashboard_dir, o)
        ont_results_path = os.path.join(ont_dashboard_dir, "dashboard.yml")
        ont_results = ontologies_results[o]

        if os.path.exists(ont_results_path) and config.is_skip_existing():
            continue

        logging.info(f"Computing final metrics for {o}")
        if 'metrics' in ont_results and 'failure' not in ont_results:
            if o in ontology_use:
                uses = ontology_use[o]
                ### Computing dashboard score
                if 'base_prefixes' in ont_results:
                    for base_prefix in ont_results['base_prefixes']:
                        if base_prefix in ontology_use and base_prefix in ontology_base_prefixes:
                            uses.extend(ontology_base_prefixes[base_prefix])
                uses = list(set(uses))
            else:
                uses = []
                uses.append(o)
                logging.warning(f"{o} has no registered uses, but should, at least, use itself. This is usually an "
                                f"indication that the prefix is unknown.")
            uses_count = len(uses) - 1
            uses.sort()

            dashboard_score = {}
            dashboard_score['_impact_external'] = compute_external_impact(ont_results['metrics']['Info: How many externally documented uses?'])
            dashboard_score['_impact'] = round_float(float(uses_count)/len(ontologies))
            dashboard_score['_reuse'] = round_float(float(ont_results['metrics']['Entities: % of entities reused'])/100)

            dashboard_html = os.path.join(ont_dashboard_dir, "dashboard.html")

            # Metrics should be completely computed for this the dashboard to be executed.
            force = True
            if os.path.exists(dashboard_html):
                force = False
                modified_timestamp = os.path.getmtime(dashboard_html)
                hours_since = get_hours_since(modified_timestamp)
                if hours_since >= config.get_force_regenerate_dashboard_after_hours():
                    logging.info(f"{dashboard_html} has been generated more than {hours_since} hours ago, so "
                                 f"forcing dashboard generation..")
                    force = True
            elif 'last_ontology_dashboard_run_failed' in ont_results and ont_results['last_ontology_dashboard_run_failed']:
                force = False
                modified_timestamp = os.path.getmtime(ont_results_path)
                hours_since = get_hours_since(modified_timestamp)
                if hours_since >= config.get_force_regenerate_dashboard_after_hours():
                    logging.info(f"{dashboard_html} has been generated more than {hours_since} hours ago, so "
                                 f"forcing dashboard generation..")
                    force = True
            if force or ont_results['changed']:
                logging.info(f"Creating dashboard for {o}...")
                try:
                    # Only overwrite these metrics when we actually overwrite the dashboard..
                    ont_results['metrics']['Info: Which ontologies use it?'] = [use for use in uses if use != o]
                    ont_results['metrics']['Info: How many ontologies use it?'] = uses_count
                    if 'Info: Experimental OBO score' in ont_results['metrics']:
                        ont_results['metrics']['Info: Experimental OBO score'].update(dashboard_score)
                    else:
                        ont_results['metrics']['Info: Experimental OBO score'] = dashboard_score
                    save_yaml(ont_results, ont_results_path)
                    runcmd(f"make  {make_parameters} {dashboard_html}", config.get_dashboard_report_timeout_seconds())
                    ont_results.pop('last_ontology_dashboard_run_failed', None)

                except Exception:
                    logging.exception(f'Failed to build dashboard pages for {o}.')
                    ont_results['failure'] = 'failed_ontology_dashboard'
                    ont_results['last_ontology_dashboard_run_failed'] = True
                    save_yaml(ont_results, ont_results_path)
                    create_dashboard_qc_badge("red", "Processing error: build dashboard", ont_dashboard_dir)
                    create_dashboard_score_badge("lightgrey", "NA", ont_dashboard_dir)
                    continue
            else:
                logging.info(f"Not running dashboard for {o} because it has not changed ({ont_results['changed']}) "
                             f"nor forced ({force})..")
        else:
            logging.info(f"{o} has a results file, but no metrics were computed ({'metrics' not in ont_results}), "
                         f"or a failure registered ({'failure' not in ont_results})). "
                         f"This suggests there was an error with the basefile computation, so we"
                         f"dont even try to generate the dashboard.")


if __name__ == '__main__':
    cli()
