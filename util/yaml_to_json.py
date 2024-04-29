#!/usr/bin/env python3

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

import yaml

def datetime_serializer(o):
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError("Type not serializable")

def main(args=None):
    d = 'description'
    parser = argparse.ArgumentParser(description=d)
    parser.add_argument('yamlfile', type=str, help='File(s) to convert.')
    args = parser.parse_args(args)

    yamlfile = Path(args.yamlfile)
    if not (yamlfile.exists() and yamlfile.is_file()):
        raise ValueError("Input arg must exist and be a file")
    with open(yamlfile) as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError("Input arg does not appear to be valid YAML")

    json_path = yamlfile.parent / f"{yamlfile.stem}.json"
    with open(json_path, "w") as f:
        json.dump(data, f, default=datetime_serializer, indent=2)


if __name__ == '__main__':
    sys.exit(main())
