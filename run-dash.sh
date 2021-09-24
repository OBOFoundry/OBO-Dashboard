#!/usr/bin/env bash

set -e

OBODASH="sh odk.sh obodash"

rm -rf dashboard ontologies
mkdir -p dashboard ontologies
#$OBODASH refresh -B
$OBODASH -C dashboard-config.yml