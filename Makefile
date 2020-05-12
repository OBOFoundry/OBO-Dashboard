MAKEFLAGS += --warn-undefined-variables

n.PHONY: all all-big all-small clean db refresh 

# -------------------- #
### GLOBAL VARIABLES ###
# -------------------- #

ROBOT := java -Xmx10G -jar build/robot.jar
YML_URL := https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/ontologies.yml

# List of ontology ids;  Run `make refresh` to update
ONT_IDS := $(shell cat ontologies.txt)
ONTS_OWL := $(addprefix build/ontologies/, $(addsuffix .owl, $(ONT_IDS)))

# Large ontologies
BIG_ONT_IDS := bto chebi dron gaz ncbitaxon ncit pr uberon

# All remaining ontologies
SMALL_ONT_IDS := $(filter-out $(BIG_ONT_IDS), $(ONT_IDS))

# --------------------------------------------------------- #
### MAKE COMMANDS TO BUILD, DOWNLAOD, OR CLEAN ONTOLOGIES ###
# --------------------------------------------------------- #

# Main tasks
#all: db
all: ontologies.txt | dependencies
	@make $(ONT_IDS)

all-big: ontologies.txt | dependencies
	@make $(BIG_ONT_IDS)

all-small: ontologies.txt | dependencies
	@make $(SMALL_ONT_IDS)


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

# Just the ontology IDs
ontologies.txt: ontologies.yml
	cat $< | sed -n 's/  id: \([A-Za-z0-9_]*\)/\1/p' | sed '/^. / d' | sort -u > $@ 

$(BIG_ONT_IDS): | build/ontologies
	$(eval ONT_ID := $@)
	@make build/ontologies/$(ONT_ID).owl

$(SMALL_ONT_IDS): dependencies/obo_context.jsonld |  build/ontologies
	$(eval ONT_ID := $@)
	@make build/ontologies/$(ONT_ID).owl
	$(eval CREATE_BASE := $(shell python3 util/create_base_ontology.py $(ONT_ID) $<))
	@echo '$(CREATE_BASE)'


######### THIS WORKS BUT I WANT TO DO THIS WITH PYTHON CODE ######################
#	@echo 'determining if base namespace exists for $(ONT_ID)'
#	$(eval BASE_NS := $(shell python3 util/get_base_ns.py $< $(ONT_ID)))
#	@echo 'base namespace: $(BASE_NS)'	

#	@if [ '$(BASE_NS)' == '' ]; then \
#	  echo "*** Base namespace for '$(ONT_ID)' not found. This is hack to skip blank namespaces! ***"; \
#	else \
#	  echo "*** Creating base ontology for '$(ONT_ID)'"; \
#	  $(ROBOT) remove -i build/ontologies/$@.owl \
#	    --base-iri $(BASE_NS) \
#	    --axioms external \
#	    -p false \
#	    --output build/ontologies/$@.tmp.owl; \
#	  mv build/ontologies/$@.tmp.owl build/ontologies/$@.owl; \
#	fi
####################################################################################


build/ontologies/%.owl: dependencies/obo_context.jsonld | build/ontologies build/robot.jar
	curl -Lk -o $@ http://purl.obolibrary.org/obo/$(notdir $@)
	@echo '*** $@ downloaded'

###################
# Assets contains SVGs for icons
# These will be included in the ZIP
SVGS ?= dashboard/assets/check.svg dashboard/assets/info.svg dashboard/assets/warning.svg dashboard/assets/x.svg


# Every ontology ID gets its own task
#$(ONTS):%: dashboard/%/dashboard.html
#	@echo "making $(%)"


# ------------------- #
### DIRECTORY SETUP ###
# ------------------- #

# Create needed directories
#dependencies build dashboard dashboard/assets build/ontologies:
dependencies build dashboard dashboard/assets build/ontologies:
	mkdir -p $@

# --------------- #
### ROBOT SETUP ###
# --------------- #

build/robot.jar: | build
	curl -o $@ -Lk https://github.com/ontodev/robot/releases/download/v1.5.0/robot.jar


# ------------------------------ #
### EXTERNAL FILE DEPENDENCIES ###
# ------------------------------ #

# Registry YAML
ontologies.yml:
	curl -Lk -o $@ https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/ontologies.yml

# OBO Prefixes
dependencies/obo_context.jsonld: dependencies
	curl -Lk -o $@ https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/obo_context.jsonld

# Schemas
dependencies/license.json: dependencies
	curl -Lk -o $@ https://github.com/OBOFoundry/OBOFoundry.github.io/raw/master/util/schema/license.json

dependencies/contact.json: dependencies
	curl -Lk -o $@ https://github.com/OBOFoundry/OBOFoundry.github.io/raw/master/util/schema/contact.json

# RO is used to compare properties
dependencies/ro-merged.owl: | dependencies build/robot.jar
	$(ROBOT) merge --input-iri http://purl.obolibrary.org/obo/ro.owl --output $@

build/ro-properties.csv: util/get_properties.rq dependencies/ro-merged.owl | build/robot.jar
	$(ROBOT) query --input $(word 2,$^) --query $< $@

# Download SVGs from open iconic
dashboard/assets/%.svg: | dashboard/assets
	curl -Lk -o $@ https://raw.githubusercontent.com/iconic/open-iconic/master/svg/$(notdir $@)

# ------------------- #
### DASHBOARD FILES ###
# ------------------- #

# Regular size ontologies for which we can build base files
# BASE_FILES := $(foreach O, $(SMALL_ONTS), build/ontologies/$(O).owl)
#.PRECIOUS: $(BASE_FILES)

# $(BASE_FILES): util/get_base_ns.py dependencies/obo_context.jsonld | build/ontologies build/robot.jar
# 	$(eval BASE := $(basename $(notdir $@)))
# 	$(eval BASE_NS := $(shell python3 $^ $(BASE)))
# 	
# 	@if [ '$(BASE_NS)' == '' ]; then \
# 	  echo "************* Base namespace (BASE_NS) for '$(BASE)' not found. This is hack to skip blank namespaces! ************* "; \
# 	else \
# 	  $(ROBOT) merge --input-iri http://purl.obolibrary.org/obo/$(notdir $@) \
# 	  remove --base-iri $(BASE_NS) --axioms external -p false --output $@; \
# 	fi

# Large ontologies that we cannot load into memory to build base file
#FULL_FILES := $(foreach O, $(filter-out $(SMALL_ONTS), $(ONTS)), build/ontologies/$(O).owl)
#.PRECIOUS: $(FULL_FILES)
#$(FULL_FILES): | build/ontologies
#	curl -Lk -o $@ http://purl.obolibrary.org/obo/$(notdir $@)

# dashboard.py has several dependencies, and generates four files,
.PRECIOUS: dashboard/%/dashboard.yml dashboard/%/robot_report.tsv dashboard/%/fp3.tsv dashboard/%/fp7.tsv
dashboard/%/dashboard.yml dashboard/%/robot_report.tsv dashboard/%/fp3.tsv dashboard/%/fp7.tsv: util/dashboard/dashboard.py build/ontologies/%.owl ontologies.yml dependencies/license.json dependencies/contact.json build/ro-properties.csv | build/robot.jar
	python3 $^ $(dir $@)

# HTML output of ROBOT report
.PRECIOUS: dashboard/%/robot_report.html
dashboard/%/robot_report.html: util/create_report_html.py dashboard/%/robot_report.tsv dependencies/obo_context.jsonld util/templates/report.html.jinja2
	python3 $^ "ROBOT Report - $*" $@

# HTML output of IRI report
.PRECIOUS: dashboard/%/fp3.html
dashboard/%/fp3.html: util/create_report_html.py dashboard/%/fp3.tsv dependencies/obo_context.jsonld util/templates/report.html.jinja2
	python3 $^ "IRI Report - $*" $@

# HTML output of Relations report
.PRECIOUS: dashboard/%/fp7.html
dashboard/%/fp7.html: util/create_report_html.py dashboard/%/fp7.tsv dependencies/obo_context.jsonld util/templates/report.html.jinja2
	python3 $^ "Relations Report - $*" $@

# Convert dashboard YAML to HTML page
.PRECIOUS: dashboard/%/dashboard.html
dashboard/%/dashboard.html: util/create_ontology_html.py dashboard/%/dashboard.yml util/templates/ontology.html.jinja2 dashboard/%/robot_report.html dashboard/%/fp3.html dashboard/%/fp7.html | $(SVGS)
	python3 $(wordlist 1,3,$^) $@

# -------------------------- #
### MERGED DASHBOARD FILES ###
# -------------------------- #

# Combined summary for all OBO foundry ontologies
.PRECIOUS: dashboard/index.html
#dashboard/index.html: util/create_dashboard_html.py dependencies/ontologies.yml util/templates/index.html.jinja2 $(ONTS) | $(SVGS)
dashboard/index.html: util/create_dashboard_html.py ontologies.yml util/templates/index.html.jinja2
	$(eval ROBOT_VERSION := $(shell $(ROBOT) -version))
	$(eval OBOMD_VERSION := $(shell curl https://api.github.com/repos/OBOFoundry/OBO-Dashboard/commits | jq '.[0].html_url'))
	python3 $< dashboard $(word 2,$^) "$(ROBOT_VERSION)" "$(OBOMD_VERSION)" $@

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
