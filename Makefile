### Configuration
#
# These are standard options to make Make sane:
# <http://clarkgrubb.com/makefile-style-guide#toc2>
MAKEFLAGS += --warn-undefined-variables
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := all
.DELETE_ON_ERROR:
.SUFFIXES:
.SECONDARY:


# ----------------- #
### MAKE COMMANDS ###
# ----------------- #

# Main tasks
all: db
db: dashboard/index.html dashboard/about.html

# Update ontologies.txt
refresh:
	rm -f ontologies.txt
	make ontologies.txt

# Just the ontology IDs
ontologies.txt: dependencies/ontologies.yml
	cat $< | sed -n 's/  id: \([A-Za-z0-9_]*\)/\1/p' | sed '/^. / d' > $@

# List of all ontology IDs
# Run `make refresh` to update
ONTS = $(shell cat ontologies.txt)

# Every ontology ID gets its own task
$(ONTS):%: dashboard/%/dashboard.html

# Remove build directories
# WARNING: This will delete *ALL* dashboard files!
clean:
	rm -rf build dashboard dependencies

# ------------------- #
### DIRECTORY SETUP ###
# ------------------- #

# Create needed directories
dependencies build dashboard dashboard/assets build/ontologies:
	mkdir -p $@

# --------------- #
### ROBOT SETUP ###
# --------------- #

ROBOT := java -Xmx10G -jar build/robot.jar

build/robot.jar: | build
	curl -o $@ -Lk https://github.com/ontodev/robot/releases/download/v1.5.0/robot.jar

# ------------------------- #
### EXTERNAL DEPENDENCIES ###
# ------------------------- #

GITHUB := https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master

# Registry YAML
dependencies/ontologies.yml: | dependencies
	curl -Lk -o $@ $(GITHUB)/registry/ontologies.yml

# OBO Prefixes
dependencies/obo_context.jsonld: | dependencies
	curl -Lk -o $@ $(GITHUB)/registry/obo_context.jsonld

# Schemas
dependencies/license.json: | dependencies
	curl -Lk -o $@ $(GITHUB)/util/schema/license.json

dependencies/contact.json: | dependencies
	curl -Lk -o $@ $(GITHUB)/util/schema/contact.json

# RO is used to compare properties
dependencies/ro-merged.owl: | dependencies build/robot.jar
	$(ROBOT) merge --input-iri http://purl.obolibrary.org/obo/ro.owl --output $@

build/ro-properties.csv: dependencies/ro-merged.owl | build/robot.jar
	$(ROBOT) query --input $< --query util/get_properties.rq $@

# Assets contains SVGs for icons
# These will be included in the ZIP
SVGS := dashboard/assets/check.svg \
dashboard/assets/info.svg \
dashboard/assets/warning.svg \
dashboard/assets/x.svg

# Download SVGs from open iconic
dashboard/assets/%.svg: | dashboard/assets
	curl -Lk -o $@ https://raw.githubusercontent.com/iconic/open-iconic/master/svg/$(notdir $@)

# ------------------- #
### DASHBOARD FILES ###
# ------------------- #

# Large ontologies
BIG_ONTS := bto chebi dron gaz ncbitaxon ncit pr uberon

# All remaining ontologies
SMALL_ONTS := $(filter-out $(BIG_ONTS), $(ONTS))

# Regular size ontologies for which we can build base files
BASE_FILES := $(foreach O, $(SMALL_ONTS), build/ontologies/$(O).owl)
$(BASE_FILES): | build/ontologies build/robot.jar
	$(eval BASE_NS := $(shell python3 util/get_base_ns.py $(basename $(notdir $@)) dependencies/obo_context.jsonld))
	$(ROBOT) merge --input-iri http://purl.obolibrary.org/obo/$(notdir $@) \
	 remove --base-iri $(BASE_NS) --axioms external -p false --output $@

# Large ontologies that we cannot load into memory to build base file
FULL_FILES := $(foreach O, $(filter-out $(SMALL_ONTS), $(ONTS)), build/ontologies/$(O).owl)
$(FULL_FILES): | build/ontologies
	curl -Lk -o $@ http://purl.obolibrary.org/obo/$(notdir $@)

# dashboard.py has several dependencies, and generates four files,
dashboard/%/dashboard.yml dashboard/%/robot_report.tsv dashboard/%/fp3.tsv dashboard/%/fp7.tsv: util/dashboard/dashboard.py build/ontologies/%.owl dependencies/ontologies.yml dependencies/license.json dependencies/contact.json build/ro-properties.csv | build/robot.jar
	python3 $^ $(dir $@)

# HTML output of ROBOT report
dashboard/%/robot_report.html: util/create_report_html.py dashboard/%/robot_report.tsv dependencies/obo_context.jsonld util/templates/report.html.jinja2
	python3 $^ "ROBOT Report - $*" $@

# HTML output of IRI report
dashboard/%/fp3.html: util/create_report_html.py dashboard/%/fp3.tsv dependencies/obo_context.jsonld util/templates/report.html.jinja2
	python3 $^ "IRI Report - $*" $@

# HTML output of Relations report
dashboard/%/fp7.html: util/create_report_html.py dashboard/%/fp7.tsv dependencies/obo_context.jsonld util/templates/report.html.jinja2
	python3 $^ "Relations Report - $*" $@

# Convert dashboard YAML to HTML page
dashboard/%/dashboard.html: util/create_ontology_html.py dashboard/%/dashboard.yml util/templates/ontology.html.jinja2 dashboard/%/robot_report.html dashboard/%/fp3.html dashboard/%/fp7.html | $(SVGS)
	python3 $(wordlist 1,3,$^) $@
	@echo "Created $@"

# -------------------------- #
### MERGED DASHBOARD FILES ###
# -------------------------- #

# Combined summary for all OBO foundry ontologies
# Rebuild whenever an HTML page changes
dashboard/index.html: util/create_dashboard_html.py $(ONTS) util/templates/index.html.jinja2 | $(SVGS)
	python3 $< dashboard dependencies/ontologies.yml $@

# More details for users
dashboard/about.html: docs/about.md util/templates/about.html.jinja2
	python3 util/md_to_html.py $< -t $(word 2,$^) -o $@

# ------------- #
### PACKAGING ###
# ------------- #

# Create ZIP for archive and remove dashboard folder
dashboard.zip: dashboard/index.html dashboard/about.html
	zip -r $@ dashboard/*
