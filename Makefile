# ----------------- #
### MAKE COMMANDS ###
# ----------------- #

# Main tasks
db: dashboard/index.html dashboard/about.html $(SVGS)
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
	rm -rf dashboard

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

ROBOT := java -Xmx10G -jar build/robot.jar

build/robot.jar: | build
	curl -o $@ -Lk \
	https://github.com/ontodev/robot/releases/download/v1.5.0/robot.jar

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

# RO is used to compare properties
dependencies/ro-merged.owl: | dependencies build/robot.jar
	$(ROBOT) merge --input-iri http://purl.obolibrary.org/obo/ro.owl --output $@

# ------------------- #
### DASHBOARD FILES ###
# ------------------- #

# All registry ontologies from ontologies.txt
# OR just whatever was specified in ONTS variable
ONTS := $(or ${ONTS},${ONTS}, $(shell cat dependencies/ontologies.txt))

# Large ontologies
BIG_ONTS := bto chebi dron gaz ncbitaxon ncit pr uberon

# All remaining ontologies
SMALL_ONTS := $(filter-out $(BIG_ONTS), $(ONTS))

# Regular size ontologies for which we can build base files
BASE_FILES := $(foreach O, $(SMALL_ONTS), build/ontologies/$(O).owl)
$(BASE_FILES): | build/robot.jar build/ontologies
	$(eval BASE_NS := $(shell python3 util/get_base_ns.py $(basename $(notdir $@)) dependencies/obo_context.jsonld))
	$(ROBOT) merge --input-iri http://purl.obolibrary.org/obo/$(notdir $@) \
	 remove --base-iri $(BASE_NS) --axioms external -p false --output $@

# Large ontologies that we cannot load into memory to build base file
FULL_FILES := $(foreach O, $(filter-out $(SMALL_ONTS), $(ONTS)), build/ontologies/$(O).owl)
$(FULL_FILES): | build/ontologies
	curl -Lk -o $@ http://purl.obolibrary.org/obo/$(notdir $@)

# Report outputs
YAML_REPORTS := $(foreach O, $(ONTS), dashboard/$(O)/dashboard.yml)
HTML_REPORTS := $(foreach O, $(ONTS), dashboard/$(O)/dashboard.html)
ROBOT_REPORTS := $(foreach O, $(ONTS), dashboard/$(O)/robot_report.html)
FP3_REPORTS := $(foreach O, $(ONTS), dashboard/$(O)/fp3.html)
FP7_REPORTS := $(foreach O, $(ONTS), dashboard/$(O)/fp7.html)
ALL_REPORTS := $(HTML_REPORTS) $(ROBOT_REPORTS) $(FP3_REPORTS) $(FP7_REPORTS)

# TODO - only update whenever the ontology changes
# Some sort of rebuild script which deletes the YAML file?
.PRECIOUS: dashboard/%/dashboard.yml
dashboard/%/dashboard.yml: util/dashboard/dashboard.py build/ontologies/%.owl | build/robot.jar
	@python3 $< -i $(word 2, $^) -y dependencies/ontologies.yml -r dependencies/ro-merged.owl

# Convert dashboard YAML to HTML page
# Rebuild whenever YAML changes
# Also prompts the builds of the HTML reports
.PRECIOUS: dashboard/%/dashboard.html
dashboard/%/dashboard.html: util/create_ontology_html.py dashboard/%/dashboard.yml util/templates/ontology.html.jinja2
	@python3 $< $(dir $@) $@
	@echo "Created $@"

# HTML output of ROBOT report
.PRECIOUS: dashboard/%/robot_report.html
dashboard/%/robot_report.html: util/create_report_html.py dashboard/%/dashboard.yml util/templates/report.html.jinja2
	@python3 $< $(dir $@)/robot_report.tsv \
	 "ROBOT Report - $(lastword $(subst /, , $(dir $@)))" \
	 dependencies/obo_context.jsonld $@ || true

# HTML output of IRI report
.PRECIOUS: dashboard/%/fp3.html
dashboard/%/fp3.html: util/create_report_html.py dashboard/%/dashboard.yml util/templates/report.html.jinja2
	@python3 $< $(dir $@)/fp3.tsv \
	 "IRI Report - $(lastword $(subst /, , $(dir $@)))" \
	 dependencies/obo_context.jsonld $@ || true

# HTML output of Relations report
.PRECIOUS: dashboard/%/fp7.html
dashboard/%/fp7.html: util/create_report_html.py dashboard/%/dashboard.yml util/templates/report.html.jinja2
	@python3 $< $(dir $@)/fp7.tsv \
	 "Relations Report - $(lastword $(subst /, , $(dir $@)))" \
	 dependencies/obo_context.jsonld $@ || true

# -------------------------- #
### MERGED DASHBOARD FILES ###
# -------------------------- #

# Assets contains SVGs for icons
# These will be included in the ZIP
SVGS := dashboard/assets/check.svg \
dashboard/assets/info.svg \
dashboard/assets/warning.svg \
dashboard/assets/x.svg

# Download SVGs from open iconic
dashboard/assets/%.svg: | dashboard/assets
	curl -Lk -o $@ https://raw.githubusercontent.com/iconic/open-iconic/master/svg/$(notdir $@)

# Combined summary for all OBO foundry ontologies
# Rebuild whenever an HTML page changes
.PRECIOUS: dashboard/index.html
dashboard/index.html: util/create_dashboard_html.py $(ALL_REPORTS) util/templates/index.html.jinja2 | $(SVGS)
	python3 $< dashboard dependencies/ontologies.yml $@

# More details for users
.PRECIOUS: dashboard/about.html
dashboard/about.html: docs/about.md util/templates/about.html.jinja2
	python3 util/md_to_html.py $< -t $(word 2,$^) -o $@

# ------------- #
### PACKAGING ###
# ------------- #

# Create ZIP for archive and remove dashboard folder
dashboard.zip: dashboard/index.html dashboard/about.html
	zip -r $@ dashboard/*
