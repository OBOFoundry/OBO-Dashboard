#!/usr/bin/env python3
#
# Read the git history of the `dashboard/dashboard-results.yml` file,
# and generate a table of passing check counts on each date.

import csv
import subprocess
import yaml

from collections import defaultdict
from datetime import datetime


def list_commits(path):
    """Given a file path,
    return a list of dates and commit hashes
    for each commit that modified that file."""
    process = subprocess.run(
        ["git", "log", "--follow", "--reverse", "--", path],
        check=True,
        text=True,
        stdout=subprocess.PIPE
    )
    commits = []
    commit = None
    for line in process.stdout.splitlines():
        if line.startswith("commit "):
            commit = line.replace("commit ", "").strip()
        elif line.startswith("Date: "):
            date = line.replace("Date: ", "").strip()
            dt = datetime.strptime(date, '%a %b %d %H:%M:%S %Y %z')
            ymd = dt.strftime("%Y-%m-%d")
            commits.append([ymd, commit])
    return commits


def summarize_run(data):
    """Given a dashboard-results YAML
    return a dictionary from principles to counts
    of FP* checks that passed,
    and the total number of ontologies."""
    result = defaultdict(int)
    for ontology in data["ontologies"]:
        result["total"] += 1
        if "results" not in ontology:
            continue
        for key, value in ontology["results"].items():
            if not key.startswith("FP"):
                continue
            if "status" not in value:
                continue
            if value["status"] != "PASS":
                continue
            result[key] += 1
    return result


def read_yaml(path, commit):
    """Given a file path and a commit hash,
    read the file as YAML and return the contents."""
    process = subprocess.run(
        ["git", "show", commit + ":" + path],
        check=True,
        text=True,
        stdout=subprocess.PIPE
    )
    return yaml.safe_load(process.stdout)


def main():
    """Read all the versions of dashboard-results
    in the git history
    and write a `summary.tsv` with counts by date."""
    path = "dashboard/dashboard-results.yml"
    commits = list_commits(path)
    rows = []
    for (date, commit) in commits:
        data = read_yaml(path, commit)
        row = summarize_run(data)
        row["date"] = date
        rows.append(row)

    fieldnames = list(rows[-1].keys())
    fieldnames.sort(key=str.casefold)
    with open("summary.tsv", "w") as f:
        w = csv.DictWriter(
            f, fieldnames=fieldnames, delimiter="\t", lineterminator="\n"
        )
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
