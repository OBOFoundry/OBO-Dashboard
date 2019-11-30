# ------------------ #
### MAIN VARIABLES ###
# ------------------ #

# Dashboard build directory
DASH := dashboard

# ROBOT command
ROBOT := java -jar build/robot.jar

# Report files
YAML_REPORTS := $(foreach O, $(shell cat dependencies/ontologies.txt), $(DASH)/$(O)/dashboard.yml)
HTML_REPORTS := $(foreach O, $(shell cat dependencies/ontologies.txt), $(DASH)/$(O)/dashboard.html)
ROBOT_REPORTS := $(foreach O, $(shell cat dependencies/ontologies.txt), $(DASH)/$(O)/robot_report.html)
FP3_REPORTS := $(foreach O, $(shell cat dependencies/ontologies.txt), $(DASH)/$(O)/fp3.html)
FP7_REPORTS := $(foreach O, $(shell cat dependencies/ontologies.txt), $(DASH)/$(O)/fp7.html)

# Assets contains SVGs for icons
# These will be included in the ZIP
SVGS := $(DASH)/assets/check.svg \
$(DASH)/assets/info.svg \
$(DASH)/assets/warning.svg \
$(DASH)/assets/x.svg \

# ----------------- #
### MAKE COMMANDS ###
# ----------------- #

# We always need to make the dependencies first
# Then run the dashboard
all:
	make prepare
	make dashboard

# Make the ZIP (everything)
dashboard: build/dashboard.zip

# Make all and then remove build directory
clean:
	make all
	rm -rf build

svgs: $(SVGS)

# ------------------- #
### DIRECTORY SETUP ###
# ------------------- #

# Create needed directories
dependencies build $(DASH):
	mkdir -p $@

$(DASH)/assets: $(DASH)
	mkdir -p $@

# ------------------------- #
### EXTERNAL DEPENDENCIES ###
# ------------------------- #

prepare: dependencies/ontologies.txt \
dependencies/obo_context.jsonld \
dependencies/license.json \
dependencies/contact.json \
dependencies/ro-merged.owl

# Registry YAML
dependencies/ontologies.yml: | dependencies
	curl -Lk -o $@ \
	https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/ontologies.yml

# Just the ontology IDs
dependencies/ontologies.txt: dependencies/ontologies.yml
	cat $< | sed -n 's/  id: \([A-Za-z0-9_]*\)/\1/p' | sed '/^. / d' > $@

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

# Download SVGs from open iconic
$(DASH)/assets/%.svg: | $(DASH)/assets
	curl -Lk -o $@ https://raw.githubusercontent.com/iconic/open-iconic/master/svg/$(notdir $@)

# RO is used to compare properties
dependencies/ro-merged.owl: | dependencies build/robot.jar
	$(ROBOT) merge --input-iri http://purl.obolibrary.org/obo/ro.owl --output $@

# -------------- #
### ROBOT JARS ###
# -------------- #

# This version of ROBOT includes features for starting Py4J
# This will be changed to ROBOT release once feature is released
build/robot.jar: | build
	curl -o $@ -Lk \
	https://github.com/ontodev/robot/releases/download/v1.5.0/robot.jar

# --------------------------- #
### DASHBOARD FUNCTIONALITY ###
# --------------------------- #

# TODO - only update whenever the ontology changes
# Some sort of rebuild script which deletes the YAML file?
.PRECIOUS: $(DASH)/%/dashboard.yml
$(DASH)/%/dashboard.yml:
	$(eval O := $(lastword $(subst /, , $(dir $@))))
	@mkdir -p $(dir $@)
	@./util/dashboard/dashboard.py $(O) dependencies/ontologies.yml dependencies/ro-merged.owl $(dir $@)

# Convert dashboard YAML to HTML page
# Rebuild whenever YAML changes
# Also prompts the builds of the HTML reports
.PRECIOUS: $(DASH)/%/dashboard.html
$(DASH)/%/dashboard.html: $(DASH)/%/dashboard.yml
	@./util/create_ontology_html.py $(dir $@) $@
	@echo "Created $@"

# HTML output of ROBOT report
.PRECIOUS: $(DASH)/%/robot_report.html
$(DASH)/%/robot_report.html: $(DASH)/%/dashboard.yml
	@./util/create_report_html.py \
	 $(dir $@)/robot_report.tsv \
	 "ROBOT Report - $(lastword $(subst /, , $(dir $@)))" \
	 dependencies/obo_context.jsonld $@ || true

# HTML output of IRI report
.PRECIOUS: $(DASH)/%/fp3.html
$(DASH)/%/fp3.html: $(DASH)/%/dashboard.yml
	@./util/create_report_html.py \
	 $(dir $@)/fp3.tsv \
	 "IRI Report - $(lastword $(subst /, , $(dir $@)))" \
	 dependencies/obo_context.jsonld $@ || true

# HTML output of Relations report
.PRECIOUS: $(DASH)/%/fp7.html
$(DASH)/%/fp7.html: $(DASH)/%/dashboard.yml
	@./util/create_report_html.py \
	 $(dir $@)/fp7.tsv \
	 "Relations Report - $(lastword $(subst /, , $(dir $@)))" \
	 dependencies/obo_context.jsonld $@ || true

# Combined summary for all OBO foundry ontologies
# Rebuild whenever an HTML page changes
.PRECIOUS: $(DASH)/index.html
$(DASH)/index.html: $(HTML_REPORTS) $(ROBOT_REPORTS) $(FP3_REPORTS) $(FP7_REPORTS) $(DASH)/assets
	./util/create_dashboard_html.py $(DASH) dependencies/ontologies.yml $@

# ------------- #
### PACKAGING ###
# ------------- #

# Create ZIP for archive
build/dashboard.zip: $(DASH)/index.html | $(SVGS)
	zip -r $@ $(DASH)/*
