# Make all files
all: dashboard/$(ONT)/dashboard.html dashboard/$(ONT)/robot_report.html dashboard/$(ONT)/fp3.html dashboard/$(ONT)/fp7.html

# ------------------- #
### DIRECTORY SETUP ###
# ------------------- #

# Create needed directories
dependencies build dashboard:
	mkdir -p $@

dashboard/assets: dashboard
	mkdir -p $@

build/ontologies: build
	mkdir -p $@

# --------------- #
### ROBOT SETUP ###
# --------------- #

ROBOT := java -jar build/robot.jar

build/robot.jar: | build
	curl -o $@ -Lk \
	https://github.com/ontodev/robot/releases/download/v1.5.0/robot.jar

# ------------------------- #
### EXTERNAL DEPENDENCIES ###
# ------------------------- #

prepare: dependencies/obo_context.jsonld dependencies/license.json dependencies/contact.json dependencies/ro-merged.owl

# Registry YAML
dependencies/ontologies.yml: | dependencies
	curl -Lk -o $@ \
	https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/ontologies.yml

# OBO Prefixes
dependencies/obo_context.jsonld: | dependencies
	curl -Lk -o $@ \
	https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/obo_context.jsonld

# Schemas
dependencies/license.json: | dependencies
	curl -Lk -o $@ \
	https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/util/schema/license.json

dependencies/contact.json: | dependencies
	curl -Lk -o $@ \
	https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/util/schema/contact.json

# RO is used to compare properties
dependencies/ro-merged.owl: | dependencies build/robot.jar
	$(ROBOT) merge --input-iri http://purl.obolibrary.org/obo/ro.owl --output $@

# Assets contains SVGs for icons
# These will be included in the ZIP
SVGS := dashboard/assets/check.svg dashboard/assets/info.svg dashboard/assets/warning.svg dashboard/assets/x.svg

# Download SVGs from open iconic
dashboard/assets/%.svg: | dashboard/assets
	curl -Lk -o $@ https://raw.githubusercontent.com/iconic/open-iconic/master/svg/$(notdir $@)

# ------------------- #
### DASHBOARD FILES ###
# ------------------- #

# Namespaces may be mixed case
# Retrieve from obo_context so that we get the correct ones
BASE_NS := $(shell python3 util/get_base_ns.py $(ONT) dependencies/obo_context.jsonld)

# Retrieve the ontology file if it doesn't exist
$(ONT).owl:
	curl -Lk -o $@ http://purl.obolibrary.org/obo/$@

# Create the base ontology file
build/ontologies/$(ONT).owl: $(ONT).owl | build/ontologies build/robot.jar
	$(ROBOT) merge --input $< \
	 remove --base-iri $(BASE_NS) --axioms external -p false --output $@

# TODO - only update whenever the ontology changes
# Some sort of rebuild script which deletes the YAML file?
.PRECIOUS: dashboard/$(ONT)/dashboard.yml
dashboard/$(ONT)/dashboard.yml: util/dashboard/dashboard.py build/ontologies/$(ONT).owl | build/robot.jar dependencies/ontologies.yml dependencies/ro-merged.owl
	python3 $< -i $(word 2, $^) -y dependencies/ontologies.yml -r dependencies/ro-merged.owl

# Convert dashboard YAML to HTML page
# Rebuild whenever YAML changes
# Also prompts the builds of the HTML reports
.PRECIOUS: dashboard/$(ONT)/dashboard.html
dashboard/$(ONT)/dashboard.html: util/create_ontology_html.py dashboard/$(ONT)/dashboard.yml util/templates/ontology.html.jinja2 | $(SVGS)
	python3 $< $(dir $@) $@

# HTML output of ROBOT report
.PRECIOUS: dashboard/$(ONT)/robot_report.html
dashboard/$(ONT)/robot_report.html: util/create_report_html.py dashboard/$(ONT)/dashboard.yml util/templates/report.html.jinja2
	python3 $< $(dir $@)/robot_report.tsv \
	 "ROBOT Report - $(lastword $(subst /, , $(dir $@)))" \
	 dependencies/obo_context.jsonld $@ || true

# HTML output of IRI report
.PRECIOUS: dashboard/$(ONT)/fp3.html
dashboard/$(ONT)/fp3.html: util/create_report_html.py dashboard/$(ONT)/dashboard.yml util/templates/report.html.jinja2
	python3 $< $(dir $@)/fp3.tsv \
	 "IRI Report - $(lastword $(subst /, , $(dir $@)))" \
	 dependencies/obo_context.jsonld $@ || true

# HTML output of Relations report
.PRECIOUS: dashboard/$(ONT)/fp7.html
dashboard/$(ONT)/fp7.html: util/create_report_html.py dashboard/$(ONT)/dashboard.yml util/templates/report.html.jinja2
	python3 $< $(dir $@)/fp7.tsv \
	 "Relations Report - $(lastword $(subst /, , $(dir $@)))" \
	 dependencies/obo_context.jsonld $@ || true
