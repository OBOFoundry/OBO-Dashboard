#!/usr/bin/env python3

import os
from py4j.protocol import Py4JJavaError


def run_report(robot_gateway, io_helper, ontology, profile=None):
    """Run and return a ROBOT Report.

    Args:
        robot_gateway (Gateway): py4j gateway to ROBOT
        io_helper (IOHelper): ROBOT IOHelper
        ontology (OWLOntology): ontology object
        profile: path to profile.txt. Optional.


    Return:
        ROBOT Report object
    """
    if ontology is None:
        return None

    report_options = robot_gateway.ReportOperation.getDefaultOptions()
    report_options['labels'] = 'false'

    if profile:
        print(profile)
        report_options['profile'] = profile

    # run the report
    try:
        report = robot_gateway.ReportOperation.getReport(
            ontology, io_helper, report_options)
    except Py4JJavaError as err:
        msg = err.java_exception.getMessage()
        print('REPORT FAILED\n' + str(msg))
        return None

    return report


class BigReport:
    """Helper class to run a Report over a large ontology. Report queries are
    run over a dataset on disk instead of in memory.
    """

    def __init__(self, robot_gateway, ns, file, profile=None):
        """Instantiate a new BigReport object by running a report over the
        ontology file.
        """
        tdb_dir = '.tdb/.{0}-tdb'.format(ns)
        if not os.path.exists('.tdb'):
            os.mkdir('.tdb')
        report_options = robot_gateway.ReportOperation.getDefaultOptions()
        report_options['tdb-directory'] = tdb_dir
        report_options['limit'] = '1'
        if profile:
            report_options['profile'] = profile
        report_options['tdb'] = 'true'
        report = None

        self.good_format = True
        try:
            print('Loading triples to {0} and running report...'.format(tdb_dir), flush=True)
            report = robot_gateway.ReportOperation.getTDBReport(file, report_options)
        except Py4JJavaError as err:
            msg = err.java_exception.getMessage()
            print('REPORT FAILED\n' + str(msg))
            self.report = None
            if 'cannot be read' in msg:
                self.good_format = False

        self.report = report

    def get_report(self):
        """Return the Report object.
        """
        return self.report

    def get_good_format(self):
        """Return True if the file provided is valid RDF/XML that can be loaded
        by Jena.
        """
        return self.get_good_format


def process_report(robot_gateway, report, ontology_dir):
    """Save the Report and return the status.

    Args:
        robot_gateway (Gateway): py4j gateway to ROBOT
        report (Report): completed Report object
        ontology_dir (str):

    Return:
        ERROR, WARN, INFO, or PASS with optional help message
    """
    outfile = os.path.join(ontology_dir, 'robot_report.tsv')
    if report is None:
        with open(outfile, 'w') as f:
            # Write empty file
            f.write("")
        return {'status': 'INFO', 'comment': 'ROBOT Report could not be generated.'}

    # print summary to terminal and save to report file
    report_options = robot_gateway.ReportOperation.getDefaultOptions()
    robot_gateway.ReportOperation.processReport(
        report, outfile, report_options)
    print('See {0} for details\n'.format(outfile))

    # return the report status
    errs = report.getTotalViolations('ERROR')
    warns = report.getTotalViolations('WARN')
    info = report.getTotalViolations('INFO')

    summary = dict()
    summary['ERROR'] = errs
    summary['WARN'] = warns
    summary['INFO'] = info

    if errs > 0:
        return {'status': 'ERROR',
                'file': 'robot_report',
                'results': summary,
                'comment': ' '.join(['{0} errors,'.format(errs),
                                     '{0} warnings,'.format(warns),
                                     '{0} info messages.'.format(info)])}
    elif warns > 0:
        return {'status': 'WARN',
                'file': 'robot_report',
                'results': summary,
                'comment': ' '.join(['{0} warnings,'.format(warns),
                                     '{0} info messages.'.format(info)])}
    elif info > 0:
        return {'status': 'INFO',
                'file': 'robot_report',
                'results': summary,
                'comment': '{0} info messages.'.format(info)}
    else:
        return {'status': 'PASS'}
