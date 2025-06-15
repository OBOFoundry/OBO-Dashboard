#!/bin/sh
# Wrapper script for docker.
#
# This is used primarily for wrapping the GNU Make workflow.
# Instead of typing "make TARGET", type "./run.sh make TARGET".
# This will run the make workflow within a docker container.
#
# The assumption is that you are working in the src/ontology folder;
# we therefore map the whole repo (../..) to a docker volume.
#
# See README-editors.md for more details.
# docker run -e ROBOT_JAVA_ARGS='-Xmx48G' -e JAVA_OPTS='-Xmx48G' \
#   -v $PWD/dashboard:/tools/OBO-Dashboard/dashboard \
#   -v $PWD/dashboard-config.yml:/tools/OBO-Dashboard/dashboard-config.yml \
#   -v $PWD/ontologies:/tools/OBO-Dashboard/build/ontologies \
#   -v $PWD/sparql:/tools/OBO-Dashboard/sparql \
#   -w /work --rm -ti obolibrary/odkfull "$@"

# This is a wrapper for the OBO Dashboard Dockerfile.
docker run -e ROBOT_JAVA_ARGS='-Xmx48G' -e JAVA_OPTS='-Xmx48G' \
  -v $PWD/dashboard-config.yml:/tools/OBO-Dashboard/dashboard-config.yml \
  -w /tools --rm -ti docker.io/library/obo-dashboard "$@"
