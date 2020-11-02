#!/usr/bin/env python3

import os
import yaml
import click
import logging
import urllib.request
from datetime import datetime

from lib import DashboardConfig, runcmd, runcmd, sha256sum, save_yaml, load_yaml, robot_prepare_ontology

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
    ontologies_path = os.path.join('dependencies', 'ontologies.yml')
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
        runcmd(f"make clean {make_parameters} -B")

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

    prepare_ontologies(ontologies['ontologies'], ontology_dir, dashboard_dir, make_parameters, config.get_redownload_after_hours())
    logging.info("Building the dashboard")
    runcmd(f"make dashboard {make_parameters} -B")
    logging.info("Postprocess files for github")
    runcmd(f"make truncate_reports_for_github {make_parameters} -B")


def prepare_ontologies(ontologies, ontology_dir, dashboard_dir, make_parameters, repeat_after_hours=24):
    for o in ontologies:
        logging.info(f"Preparing {o}...")
        ont_path = os.path.join(ontology_dir, f"{o}-raw.owl")
        ont_dashboard_dir = os.path.join(dashboard_dir, o)

        if not os.path.exists(ont_dashboard_dir):
            os.mkdir(ont_dashboard_dir)

        ont_base_path = os.path.join(ontology_dir, f"{o}.owl")
        if os.path.isfile(ont_base_path):
            modified_timestamp = os.path.getmtime(ont_base_path)
            modified_date = datetime.fromtimestamp(modified_timestamp)
            now = datetime.now()
            duration = now - modified_date
            hours_since = (duration.total_seconds() // 3600)
            if hours_since < repeat_after_hours:
                logging.info(f"File has only been downloaded recently ({hours_since} hours ago), skipping {o}. "
                             f"Redownloading after {repeat_after_hours} hours..")
                continue
            else:
                logging.info(f"File has not been downloaded recently ({hours_since} hours ago), processing {o}...")

        ont_results_path = os.path.join(ont_dashboard_dir, "dashboard.yml")
        ont_results = dict()
        ont_results['namespace'] = o
        if os.path.exists(ont_results_path):
            try:
                ont_results = load_yaml(ont_results_path)
            except Exception:
                logging.exception(f'Corrupted results file for {o}: {ont_results_path}')
                ont_results['failure'] = 'corrupted_results_file'
                save_yaml(ont_results, ont_results_path)
                continue

        try:
            ourl = ontologies[o]['mirror_from']
        except Exception:
            logging.exception(f'Missing url for {o} in registry..')
            ont_results['failure'] = 'missing_url'
            save_yaml(ont_results, ont_results_path)
            continue

        try:
            base_namespaces = ontologies[o]['base_ns']
        except Exception:
            logging.exception(f'Missing base namespaces for {o} in registry..')
            ont_results['failure'] = 'missing_base_namespaces'
            save_yaml(ont_results, ont_results_path)
            continue

        logging.info(f"Downloading {o}...")
        try:
            urllib.request.urlretrieve(ourl, ont_path)
        except Exception:
            logging.exception(f'Failed to download {o} from {ourl}')
            ont_results['failure'] = 'failed_download'
            save_yaml(ont_results, ont_results_path)
            continue

        try:
            sha256_hash = sha256sum(ont_path)
        except Exception:
            logging.exception(f'Failed to compute hashcode of {o}.')
            ont_results['failure'] = 'failed_sha256_hash'
            save_yaml(ont_results, ont_results_path)
            continue

        if 'sha256_hash' in ont_results:
            if ont_results['sha256_hash'] == sha256_hash:
                ont_results['changed'] = False
            else:
                ont_results['changed'] = True
                # If the sha changed, we should try again and
                # remove previously determined errors
                ont_results.pop('failure', None)
        else:
            ont_results['changed'] = True
            ont_results.pop('failure', None)

        ont_results['sha256_hash'] = sha256_hash
        save_yaml(ont_results, ont_results_path)

        # Only if the downloaded file changed, run the rest of the code.
        if (ont_results['changed'] == True or not os.path.isfile(ont_path)) and 'failure' not in ont_results:

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
                logging.exception(f'Failed to verify {o} as downloaded from {ourl}')
                ont_results['failure'] = 'not_an_ontology'
                save_yaml(ont_results, ont_results_path)
                continue

            logging.info(f"Creating basefile for {o}...")
            try:
                robot_prepare_ontology(ont_path, ont_base_path, base_namespaces, TIMEOUT="3600", robot_opts="-v")
            except Exception:
                logging.exception(f'Failed to compute base file for {o}.')
                ont_results['failure'] = 'failed_robot_base'
                save_yaml(ont_results, ont_results_path)
                continue
        else:
            logging.info(f"{o} has not changed since last run, skipping process.")

        dashboard_html = os.path.join(ont_dashboard_dir, "dashboard.html")

        if (ont_results['changed'] == True or 'results' not in ont_results) and 'failure' not in ont_results:
            logging.info(f"Creating dashboard for {o}...")
            try:
                runcmd(f"make  {make_parameters} {dashboard_html}")
            except Exception:
                logging.exception(f'Failed to build dashboard pages for {o}.')
                ont_results['failure'] = 'failed_ontology_dashboard'
                save_yaml(ont_results, ont_results_path)
                continue
        else:
            logging.info(f"{o} has not changed since last run, skipping dashboard building.")


if __name__ == '__main__':
    cli()
