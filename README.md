# OBO Dashboard

**The OBO Dashboard is a new feature under active development.**

The OBO Dashboard is being developed by the OBO Operations Committee and members of the Technical Working Group. Our goal is to provide a set of automated tests that establish a minimum level of compliance with OBO Principles and best practises. Keep in mind that automated checks often cannot capture the full intent of a given principle -- we do our best while keeping the automated checks as fast and cheap as possible.

For each ontology, two aspects are checked: the OBO Registry entry, and the latest release of the project's main OWL file. For each check we provide links to the rule text and implementation.

**Please give us your feedback!**

[This issue](https://github.com/OBOFoundry/OBOFoundry.github.io/issues/1076) is for general comments, with links to the specific issue for each check.


## Design

The dashboard checks rely on two sources of data for each ontology:

1. the OBO Registry entry from <http://obofoundry.org>
2. the latest OWL file

The registry entry contains information about the ontology project as a whole, while the latest OWL file is a specific version of that ontology. Various OBO principles apply to one or the other, or to both. For each principle, we have a Python script that defines the automated checks. For checks that involve the OWL files, we often rely on [ROBOT](http://robot.obolibrary.org) and its [`report`](http://robot.obolibrary.org/report) command.

For each principle, our Python script will output PASS, INFO, WARNING, or ERROR. If the result is anything other than PASS, then there will be more information. In our documentation we strive to make this clear, and suggest changes that will result in a PASS.

The results of all the checks are summarized by taking the worst result of all the checks. So the summary will be PASS only if all checks PASS.


## Developers

This code is written for a Unix (Linux/macOS) environment, and depends on standard Unix utilities, Python 3, and Java. See `requirements.txt` for the specific Python library dependencies, and the `Makefile` for all the details. You can install all Python libraries with:
```
python3 -m pip install -r requirements.txt
```

We maintain a list of OBO ontologies in `ontologies.txt` from the [OBO Registry](https://github.com/OBOFoundry/OBOFoundry.github.io). This list can always be updated if a new ontology has been added:

```
make refresh
```

### Running Over Multiple Ontologies 

The second step is to build the dashboard. This will fetch the OWL file for every OBO ontology, some of which are around 1GB in size, and run reports over them, some of which can take a long time. Expect a full build to take something like 6-7 hours.

```
make all
```

The results are put in the `build/dashboard/` directory. Consider running `make clean` to remove all generated files before starting a fresh build, as the index file will contain everything in the dashboard directory.

Once the dashboard is complete, you can compress the build into `dashboard.zip`. Note that this will compress *everything* in the dashboard directory, even if you ran the dashboard on a select set of projects (see below).
```
make dashboard.zip
```

You can also run the dashboard over a select set of ontologies by specifiying the `ONTS` variable. If you only wish to run it over one ontology, see below.
```
ONTS="obi go eco" make all
```

By manually placing OWL files in the appropriate places, you can run the dashboard on a development version of your ontology rather than the published version. For example, you could place the development version of OBI in `build/ontologies/obi.owl`.

### Running Over Single Ontologies

You can also run over a single ontology without creating an index file by referencing the ontology ID:
```
make obi
```

This will retrieve OBI and create a base version of it in `build/ontologies`. If you wish to use an existing ontology, you can place that in the `build/ontologies` directory (e.g., `build/ontologies/obi.owl`). This must have the same name as the ontology ID.
