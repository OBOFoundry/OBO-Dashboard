MAKEFLAGS += --warn-undefined-variables

.PHONY: all all-big all-small clean db refresh get-small git-big dashboard/index.html .EXPORT_ALL_VARIABLES
#dashboard/%

# -------------------- #
### GLOBAL VARIABLES ###
# -------------------- #

## robot program
ROBOT := java -Xmx10G -jar build/robot.jar
ROBOT_VERSION := $(shell $(ROBOT) -version)

## urls used in curl commands
ROBOT_URL := https://github.com/ontodev/robot/releases/download/v1.5.0/robot.jar
YML_URL := \
  https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/ontologies.yml
OBO_CONTEXT_URL := \
  https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/obo_context.jsonld
LICENSE_URL := https://github.com/OBOFoundry/OBOFoundry.github.io/raw/master/util/schema/license.json
CONTACT_URL := https://github.com/OBOFoundry/OBOFoundry.github.io/raw/master/util/schema/contact.json
RO_URL := http://purl.obolibrary.org/obo/ro.owl
OBOMD_VERSION_URL := https://api.github.com/repos/OBOFoundry/OBO-Dashboard/commits
SVG_URL := https://raw.githubusercontent.com/iconic/open-iconic/master/svg/


# List of ontology ids;  Run `make refresh` to update
ONT_IDS := $(shell cat ontologies.txt)
BIG_ONT_IDS := bto chebi dron gaz ncbitaxon ncit pr uberon
SMALL_ONT_IDS := $(filter-out $(BIG_ONT_IDS), $(ONT_IDS))


OBOMD_VERSION := $(shell curl $(OBOMD_VERSION_URL) | jq '.[0].html_url'))
#OBOMD_VERSION := "https://github.com/OBOFoundry/OBO-Dashboard/commit/06b7dfbe99a37766217b5ecc5dacb4498a964199"

## image files for reports
SVGS := \
  dashboard/assets/check.svg  dashboard/assets/info.svg  dashboard/assets/warning.svg  dashboard/assets/x.svg#


# --------------------------------------------------------- #
### MAKE COMMANDS TO BUILD, DOWNLAOD, OR CLEAN ONTOLOGIES ###
# --------------------------------------------------------- #

### Main tasks ###
all: db
	@make $(ONT_IDS)

all-big:
	$(eval ONT_IDS := $(BIG_ONT_IDS))
	@make -e db
	@make -e $(ONT_IDS)

all-small:
	$(eval ONT_IDS := $(SMALL_ONT_IDS))
	@make -e db
	@make -e $(ONT_IDS)

db: dashboard/index.html dashboard/about.html

# Remove build directories
# WARNING: This will delete *ALL* dashboard files!
clean:
	rm -rf dependencies
	rm -rf build
	rm -rf dashboard

# Update ontologies.txt
refresh:
	rm -f ontologies.txt
	rm -f ontologies.yml
	make ontologies.txt


# Every ontology ID gets its own task
#%: dashboard/%/dashboard.html
CHECK := ''
$(ONT_IDS): dependencies/obo_context.jsonld | dependencies
	@echo '*** target $@ ***'
	$(eval ONT_ID := $@)
	$(eval CHECK := $(strip $(filter $(ONT_ID), $(SMALL_ONT_IDS))))

## if small ontology try to get a base iri
ifneq ($(strip $(CHECK)),'')
	$(eval CREATE_BASE := $(shell python3 util/create_base_ontology.py $(ONT_ID) $<))
	@echo '$(CREATE_BASE)'
endif
	@make dashboard/$(ONT_ID)/dashboard.html

# ------------------- #
### DIRECTORY SETUP ###
# ------------------- #

# Create needed directories
dependencies build build/ontologies dashboard dashboard/assets:
	mkdir -p $@

build/ontologies/%.owl: \
 dependencies/obo_context.jsonld | build/ontologies build/robot.jar
	curl -Lk -o $@ http://purl.obolibrary.org/obo/$(notdir $@)
	@echo '*** $@ downloaded'

# ------------------------------ #
### EXTERNAL FILE DEPENDENCIES ###
# ------------------------------ #

build/robot.jar: | build
	curl -o $@ -Lk $(ROBOT_URL)

# Just the ontology IDs
ontologies.txt: ontologies.yml
	cat $< | sed -n 's/  id: \([A-Za-z0-9_]*\)/\1/p' | sed '/^. / d' | sort -u > $@ 

# Registry YAML
ontologies.yml:
	curl -Lk -o $@ $(YML_URL)

# OBO Prefixes
dependencies/obo_context.jsonld: dependencies
	curl -Lk -o $@ $(OBO_CONTEXT_URL)

# Schemas
dependencies/license.json: | dependencies
	curl -Lk -o $@ $(LICENSE_URL)

dependencies/contact.json: | dependencies
	curl -Lk -o $@ $(CONTACT_URL)

# RO is used to compare properties
dependencies/ro-merged.owl: | dependencies build/robot.jar
	$(ROBOT) merge --input-iri $(RO_URL) --output $@

build/ro-properties.csv: util/get_properties.rq dependencies/ro-merged.owl | build/robot.jar
	$(ROBOT) query --input $(word 2,$^) --query $< $@

# Download SVGs from open iconic
dashboard/assets/%.svg: | dashboard/assets
	curl -Lk -o $@ $(SVG_URL)$(notdir $@)

# ------------------- #
### DASHBOARD FILES ###
# ------------------- #

### dashboard.py has several dependencies, and generates four files ###
.PRECIOUS: dashboard/%/dashboard.yml dashboard/%/robot_report.tsv dashboard/%/fp3.tsv dashboard/%/fp7.tsv
dashboard/%/dashboard.yml dashboard/%/robot_report.tsv dashboard/%/fp3.tsv dashboard/%/fp7.tsv: \
 util/dashboard/dashboard.py \
 build/ontologies/%.owl \
 ontologies.yml \
 dependencies/license.json \
 dependencies/contact.json \
 build/ro-properties.csv \
 | build/robot.jar

		@echo '*** running $@: $^ $(dir $@) ***'
		@python3 $^ $(dir $@)


### HTML output of ROBOT report ###
.PRECIOUS: dashboard/%/robot_report.html
dashboard/%/robot_report.html: \
 util/create_report_html.py \
 dashboard/%/robot_report.tsv \
 dependencies/obo_context.jsonld \
 util/templates/report.html.jinja2

		@echo '*** running: $^ ROBOT Report - $* $@ ***'
		@python3 $^ "ROBOT Report - $*" $@

### HTML output of IRI report ###
.PRECIOUS: dashboard/%/fp3.html
dashboard/%/fp3.html: \
 util/create_report_html.py \
 dashboard/%/fp3.tsv \
 dependencies/obo_context.jsonld \
 util/templates/report.html.jinja2

		@echo '*** running: $^ "IRI Report - $*" $@'
		@python3 $^ "IRI Report - $*" $@

### HTML output of Relations report ###
.PRECIOUS: dashboard/%/fp7.html
dashboard/%/fp7.html: \
 util/create_report_html.py \
 dashboard/%/fp7.tsv \
 dependencies/obo_context.jsonld \
 util/templates/report.html.jinja2

		@python3 $^ "Relations Report - $*" $@

### Convert dashboard YAML to HTML page ###
.PRECIOUS: dashboard/%/dashboard.html
dashboard/%/dashboard.html: \
 util/create_ontology_html.py \
 dashboard/%/dashboard.yml \
 util/templates/ontology.html.jinja2 \
 dashboard/%/robot_report.html \
 dashboard/%/fp3.html \
 dashboard/%/fp7.html \
 | $(SVGS)
		python3 $(wordlist 1,3,$^) $@

# -------------------------- #
### MERGED DASHBOARD FILES ###
# -------------------------- #

### Combined summary for all OBO foundry ontologies ###
#.PRECIOUS: dashboard/index.html
.PHONY: dashboard/index.html
dashboard/index.html: \
 util/create_dashboard_html.py \
 ontologies.yml \
 util/templates/index.html.jinja2 \
 $(ONT_IDS) \
 | $(SVGS)
		@echo '*** target dashboard/index.html ***'
		@python3 $< dashboard $(word 2,$^) "$(ROBOT_VERSION)" "$(OBOMD_VERSION)" $@

### More details for users ###
.PRECIOUS: dashboard/about.html
dashboard/about.html: \
 docs/about.md \
 util/templates/about.html.jinja2
		@echo '*** target dashboard/about.html ***'
		@python3 util/md_to_html.py $< -t $(word 2,$^) -o $@

# ------------- #
### PACKAGING ###
# ------------- #

### Create ZIP for archive and remove dashboard folder ###
dashboard.zip: \
 dashboard/index.html \
 dashboard/about.html
		zip -r $@ dashboard/*
