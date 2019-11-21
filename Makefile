# ------------------ #
### MAIN VARIABLES ###
# ------------------ #

# Dashboard build directory
DASH := build/dashboard

# ROBOT command
ROBOT := java -jar build/robot.jar

# Report files
HTML_REPORTS := $(foreach O, $(shell cat dependencies/ontologies.txt), $(DASH)/$(O)/dashboard.html)

# Assets contains SVGs for icons
# These will be included in the ZIP
SVGS := $(DASH)/assets/check.svg \
$(DASH)/assets/info.svg \
$(DASH)/assets/warning.svg \
$(DASH)/assets/x.svg \

# ----------------- #
### MAKE COMMANDS ###
# ----------------- #

# We need to make the ontologies.txt first to get the list of IDs
all:
	make dependencies/ontologies.txt
	make dependencies/ro-merged.owl
	make dashboard

# Make the ZIP (everything)
dashboard: build/dashboard.zip

# Make all and then remove build directory
clean:
	make all
	rm -rf build

# ------------------- #
### DIRECTORY SETUP ###
# ------------------- #

# Create needed directories
dependencies build:
	mkdir -p $@

$(DASH): build
	mkdir -p $@

$(DASH)/assets: $(DASH)
	mkdir -p $@

# ------------------------- #
### EXTERNAL DEPENDENCIES ###
# ------------------------- #

# Registry YAML
dependencies/ontologies.yml:
	curl -Lk -o $@ \
	https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/registry/ontologies.yml

# Just the ontology IDs
dependencies/ontologies.txt: dependencies/ontologies.yml
	cat $< | sed -n 's/  id: \([A-Za-z0-9_]*\)/\1/p' | sed '/^. / d' > $@

# Schemas
dependencies/license.json:
	curl -Lk -o $@ \
	https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/util/schema/license.json

dependencies/contact.json:
	curl -Lk -o $@ \
	https://raw.githubusercontent.com/OBOFoundry/OBOFoundry.github.io/master/util/schema/contact.json

# Download SVGs from open iconic
$(DASH)/assets/%.svg: | $(DASH)/assets
	curl -Lk -o $@ https://raw.githubusercontent.com/iconic/open-iconic/master/svg/$(notdir $@)

# RO is used to compare properties
dependencies/ro-merged.owl: | build/robot.jar
	$(ROBOT) merge --input-iri http://purl.obolibrary.org/obo/ro.owl --output $@

# -------------- #
### ROBOT JARS ###
# -------------- #

# This version of ROBOT includes features for starting Py4J
# This will be changed to ROBOT release once feature is released
build/robot.jar: | build
	curl -o $@ -Lk \
	https://build.obolibrary.io/job/ontodev/job/robot/job/py4j/lastSuccessfulBuild/artifact/bin/robot.jar

# This version of ROBOT includes features for removing external axioms to create 'base' artefacts
# This will be removed once this feature is released
build/robot-foreign.jar: | build
	curl -o $@ -Lk \
	https://build.obolibrary.io/job/ontodev/job/robot/job/562-feature/lastSuccessfulBuild/artifact/bin/robot.jar

# --------------------------- #
### DASHBOARD FUNCTIONALITY ###
# --------------------------- #

# Reboot the JVM for Py4J
reboot:
	@bash util/reboot.sh

# TODO - only update whenever the ontology changes
# Some sort of rebuild script which deletes the YAML file
# We don't want this to depend on dependencies/ontologies.yml
# (or dependencies/ro-merged.owl) because everything would rebuild
.PRECIOUS: $(DASH)/%/dashboard.yml
$(DASH)/%/dashboard.yml: dependencies/ro-merged.owl | \
$(DASH) build/robot-foreign.jar dependencies/license.json dependencies/contact.json
	$(eval O := $(lastword $(subst /, , $(dir $@))))
	@mkdir -p $(dir $@)
	@make reboot
	@./util/dashboard/dashboard.py $(O) dependencies/ontologies.yml dependencies/ro-merged.owl $(dir $@)

# Convert dashboard YAML to HTML page
.PRECIOUS: $(DASH)/%/dashboard.html
$(DASH)/%/dashboard.html: $(DASH)/%/dashboard.yml
	@./util/create_ontology_html.py $(dir $@) $@
	@echo "Created $@"

# Combined summary for all OBO foundry ontologies
# Rebuild whenever an HTML page changes
.PRECIOUS: $(DASH)/dashboard.html
$(DASH)/dashboard.html: $(HTML_REPORTS) $(DASH)/assets/svg
	./util/create_dashboard_html.py $(DASH) dependencies/ontologies.yml $@

# ------------- #
### PACKAGING ###
# ------------- #

# Create ZIP for archive
build/dashboard.zip: $(DASH)/dashboard.html | $(SVGS)
	zip $@ $(DASH)
