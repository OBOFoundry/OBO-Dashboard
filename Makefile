# ------------------ #
### MAIN VARIABLES ###
# ------------------ #

# Dashboard build directory
DASH := dashboard

# ROBOT command
ROBOT := java -jar build/robot.jar

# Report files
ONTS := $(or ${ONTS},${ONTS}, $(shell cat dependencies/ontologies.txt))
YAML_REPORTS := $(foreach O, $(ONTS), $(DASH)/$(O)/dashboard.yml)
HTML_REPORTS := $(foreach O, $(ONTS), $(DASH)/$(O)/dashboard.html)
ROBOT_REPORTS := $(foreach O, $(ONTS), $(DASH)/$(O)/robot_report.html)
FP3_REPORTS := $(foreach O, $(ONTS), $(DASH)/$(O)/fp3.html)
FP7_REPORTS := $(foreach O, $(ONTS), $(DASH)/$(O)/fp7.html)
ALL_REPORTS := $(HTML_REPORTS) $(ROBOT_REPORTS) $(FP3_REPORTS) $(FP7_REPORTS)

# ----------------- #
### MAKE COMMANDS ###
# ----------------- #

# Main tasks
db: $(DASH)/index.html $(DASH)/about.html $(SVGS)
zip: dashboard.zip

# Prepare dependencies
# Create dashboard
all:
	make prepare
	make db

# Prepare dependencies
# Create compressed dashboard
all_zip:
	make prepare
	make zip

# Remove build directories
# WARNING: This will delete *ALL* dashboard files!
clean:
	rm -rf build
	rm -rf $(DASH)

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

# Assets contains SVGs for icons
# These will be included in the ZIP
SVGS := $(DASH)/assets/check.svg \
$(DASH)/assets/info.svg \
$(DASH)/assets/warning.svg \
$(DASH)/assets/x.svg \

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
$(DASH)/%/dashboard.yml: util/dashboard/dashboard.py | build/robot.jar
	$(eval O := $(lastword $(subst /, , $(dir $@))))
	@mkdir -p $(dir $@)
	@./$< $(O) dependencies/ontologies.yml dependencies/ro-merged.owl $(dir $@)

# Convert dashboard YAML to HTML page
# Rebuild whenever YAML changes
# Also prompts the builds of the HTML reports
.PRECIOUS: $(DASH)/%/dashboard.html
$(DASH)/%/dashboard.html: util/create_ontology_html.py $(DASH)/%/dashboard.yml util/templates/ontology.html.jinja2
	@./$< $(dir $@) $@
	@echo "Created $@"

# HTML output of ROBOT report
.PRECIOUS: $(DASH)/%/robot_report.html
$(DASH)/%/robot_report.html: util/create_report_html.py $(DASH)/%/dashboard.yml util/templates/report.html.jinja2
	@./$< $(dir $@)/robot_report.tsv \
	 "ROBOT Report - $(lastword $(subst /, , $(dir $@)))" \
	 dependencies/obo_context.jsonld $@ || true

# HTML output of IRI report
.PRECIOUS: $(DASH)/%/fp3.html
$(DASH)/%/fp3.html: util/create_report_html.py $(DASH)/%/dashboard.yml util/templates/report.html.jinja2
	@./$< $(dir $@)/fp3.tsv \
	 "IRI Report - $(lastword $(subst /, , $(dir $@)))" \
	 dependencies/obo_context.jsonld $@ || true

# HTML output of Relations report
.PRECIOUS: $(DASH)/%/fp7.html
$(DASH)/%/fp7.html: util/create_report_html.py $(DASH)/%/dashboard.yml util/templates/report.html.jinja2
	@./$< $(dir $@)/fp7.tsv \
	 "Relations Report - $(lastword $(subst /, , $(dir $@)))" \
	 dependencies/obo_context.jsonld $@ || true

# Combined summary for all OBO foundry ontologies
# Rebuild whenever an HTML page changes
.PRECIOUS: $(DASH)/index.html
$(DASH)/index.html: util/create_dashboard_html.py $(ALL_REPORTS) util/templates/index.html.jinja2 | $(SVGS)
	./$< $(DASH) dependencies/ontologies.yml $@

# More details for users
.PRECIOUS: $(DASH)/about.html
$(DASH)/about.html: docs/about.md util/templates/about.html.jinja2
	./util/md_to_html.py $< -t $(word 2,$^) -o $@

# ------------- #
### PACKAGING ###
# ------------- #

# Create ZIP for archive and remove dashboard folder
dashboard.zip: $(DASH)/index.html $(DASH)/about.html
	zip -r $@ $(DASH)/*
