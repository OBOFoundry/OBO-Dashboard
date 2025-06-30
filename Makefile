MAKEFLAGS += --warn-undefined-variables
ROBOT_JAR := build/robot.jar
REPORT_LENGTH_LIMIT := 200
ROBOT_URL := "https://github.com/ontodev/robot/releases/download/v1.9.5/robot.jar"
ROBOT_SCRIPT := "https://raw.githubusercontent.com/ontodev/robot/v1.9.5/bin/robot"
DASHBOARD_RESULTS := "dashboard/dashboard-results.yml"

# ----------------- #
### MAKE COMMANDS ###
# ----------------- #

all: dashboard
dashboard: dashboard/index.html dashboard/about.html dashboard/analysis.html

# Remove build directories
# WARNING: This will delete *ALL* dashboard files!
clean:
	rm -rf build dashboard dependencies

# Truncate potentially huge robot reports
# truncate_reports_for_github:
# 	$(eval REPORTS := $(wildcard dashboard/*/robot_report.tsv))
# 	for REP in $(REPORTS); do \
# 		touch $$REP; \
# 		cat $$REP | head -$(REPORT_LENGTH_LIMIT) > $$REP.tmp; \
# 		mv $$REP.tmp $$REP; \
# 	done

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
	curl -o $@ -Lk $(ROBOT_URL)

build/robot:
	curl -o $@ -Lk $(ROBOT_SCRIPT)

# ------------------------- #
### EXTERNAL DEPENDENCIES ###
# ------------------------- #

# OBO Prefixes
dependencies/obo_context.jsonld: dependencies
	curl -Lk -o $@ https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/obo_context.jsonld

dependencies/registry_schema.json: dependencies
	curl -Lk -o $@ https://github.com/OBOFoundry/OBOFoundry.github.io/raw/master/util/schema/registry_schema.json

# RO is used to compare properties
dependencies/ro-merged.owl: | dependencies build/robot.jar
	$(ROBOT) merge --input-iri http://purl.obolibrary.org/obo/ro.owl --output $@

build/ro-properties.csv: util/get_properties.rq dependencies/ro-merged.owl | build/robot.jar
	$(ROBOT) query --input $(word 2,$^) --query $< $@

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
# BIG_ONTS := bto chebi dron gaz ncbitaxon ncit pr uberon

# All remaining ontologies
# SMALL_ONTS := $(filter-out $(BIG_ONTS), $(ONTS))

# Regular size ontologies for which we can build base files
# BASE_FILES := $(foreach O, $(SMALL_ONTS), build/ontologies/$(O).owl)
#.PRECIOUS: $(BASE_FILES)
#$(BASE_FILES): util/get_base_ns.py dependencies/obo_context.jsonld | build/ontologies build/robot.jar
#	$(eval BASE_NS := $(shell python3 $^ $(basename $(notdir $@))))
#	$(ROBOT) merge --input-iri http://purl.obolibrary.org/obo/$(notdir $@) \
#	 remove --base-iri $(BASE_NS) --axioms external -p false --output $@ || touch $@

# Large ontologies that we cannot load into memory to build base file
#FULL_FILES := $(foreach O, $(filter-out $(SMALL_ONTS), $(ONTS)), build/ontologies/$(O).owl)
#.PRECIOUS: $(FULL_FILES)
#$(FULL_FILES): | build/ontologies
#	curl -Lk -o $@ http://purl.obolibrary.org/obo/$(notdir $@) || touch $@

# dashboard.py has several dependencies, and generates four files,
.PRECIOUS: dashboard/%/dashboard.yml dashboard/%/robot_report.tsv dashboard/%/fp3.tsv dashboard/%/fp7.tsv
dashboard/%/dashboard.yml dashboard/%/robot_report.tsv dashboard/%/fp3.tsv dashboard/%/fp7.tsv: util/dashboard/dashboard.py build/ontologies/%.owl build/ontologies/%-metrics.yml | build/robot.jar
	python3 $^ dependencies/ontologies.yml dependencies/registry_schema.json build/ro-properties.csv profile.txt dashboard-config.yml $(dir $@) $(ROBOT_JAR)

# HTML output of ROBOT report
.PRECIOUS: dashboard/%/robot_report.html
dashboard/%/robot_report.html: util/create_report_html.py dashboard/%/robot_report.tsv dependencies/obo_context.jsonld util/templates/report.html.jinja2
	echo "Processing $@"
	python3 $^ "ROBOT Report - $*" $@ $(REPORT_LENGTH_LIMIT)

# HTML output of IRI report
.PRECIOUS: dashboard/%/fp3.html
dashboard/%/fp3.html: util/create_report_html.py dashboard/%/fp3.tsv dependencies/obo_context.jsonld util/templates/report.html.jinja2
	echo "Processing $@"
	python3 $^ "IRI Report - $*" $@

# HTML output of Relations report
.PRECIOUS: dashboard/%/fp7.html
dashboard/%/fp7.html: util/create_report_html.py dashboard/%/fp7.tsv dependencies/obo_context.jsonld util/templates/report.html.jinja2
	echo "Processing $@"
	python3 $^ "Relations Report - $*" $@

# Convert dashboard YAML to HTML page
.PRECIOUS: dashboard/%/dashboard.html
dashboard/%/dashboard.html: util/create_ontology_html.py dashboard/%/dashboard.yml util/templates/ontology.html.jinja2 dashboard/%/robot_report.html dashboard/%/fp3.html dashboard/%/fp7.html | $(SVGS)
	echo "Processing $@"
	python3 $(wordlist 1,3,$^) $@

# -------------------------- #
### MERGED DASHBOARD FILES ###
# -------------------------- #

# Combined summary for all OBO foundry ontologies
.PRECIOUS: dashboard/index.html
dashboard/index.html: util/create_dashboard_html.py dependencies/ontologies.yml util/templates/index.html.jinja2 dashboard-config.yml | $(SVGS)
	$(eval ROBOT_VERSION := $(shell $(ROBOT) -version))
	$(eval OBOMD_VERSION := $(shell curl https://api.github.com/repos/OBOFoundry/OBO-Dashboard/commits | jq '.[0].html_url'))
	python3 $< dashboard $(word 2,$^) $(word 4,$^) "$(DASHBOARD_RESULTS)" "$(ROBOT_VERSION)" "$(OBOMD_VERSION)" $@

# More details for users
.PRECIOUS: dashboard/about.html
dashboard/about.html: docs/about.md util/templates/about.html.jinja2
	python3 util/md_to_html.py $< -t $(word 2,$^) -o $@

# ------------- #
### PACKAGING ###
# ------------- #

# Create ZIP for archive and remove dashboard folder
# dashboard.zip: dashboard/index.html dashboard/about.html
#	 zip -r $@ dashboard/*


test:
	python ./util/dashboard_config.py rundashboard -C dashboard-config.yml

tr: util/create_report_html.py dashboard/bfo/robot_report.tsv dependencies/obo_context.jsonld util/templates/report.html.jinja2
	python3 $^ "ROBOT Report - bfo" dashboard/bfo/robot_report.html $(REPORT_LENGTH_LIMIT)

.PRECIOUS: dashboard/analysis.html
dashboard/analysis.html: util/dashboard_analysis_html.py util/templates/analysis.html.jinja2
	python3 $< --dashboard-results $(DASHBOARD_RESULTS) --template util/templates/analysis.html.jinja2 --output $@

# When building docker image for the first time, create  builder for multi-arch builds
# This is a one-time command to create the builder.
# docker buildx create --name obo-dashboard-builder --use
build-docker-v%:
	docker buildx use obo-dashboard-builder
	docker buildx build --platform linux/amd64,linux/arm64 -t anitacaron/obo-dashboard:v$* --push .

