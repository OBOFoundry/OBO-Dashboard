# OBO Dashboard

**The OBO Dashboard is a new feature under active development.**

The OBO Dashboard is being developed by the OBO Operations Committee and members of the Technical Working Group. Our goal is to provide a set of automated tests that establish a minimum level of compliance with OBO Principles and best practises. Keep in mind that automated checks often cannot capture the full intent of a given principle -- we do our best while keeping the automated checks as fast and cheap as possible.

For each ontology, two aspects are checked: the OBO Registry entry, and the latest release of the project's main OWL file. For each check we provide links to the rule text and implementation.

**Please give us your feedback!**

[This issue](https://github.com/OBOFoundry/OBOFoundry.github.io/issues/1076) is for general comments, with links to the specific issue for each check.

---

## Limitations

This is an alpha version of an automated representation of the OBO Foundry principles. Many of the principles contain a subjective aspect, making the checks difficult to implement. These checks are still in review and subject to change.

**The result of the OBO Foundry Dashboard is not a reflection of the quality of content of an ontology.** 

It is simply a means to alert ontology developers to areas that may need review.

---

## Reading the Dashboard

The dashboard page contains a table with all results from all OBO Foundry ontologies. These results are sorted in the same order that the ontologies appear on the OBO Foundry homepage: foundry ontologies, active ontologies, orphaned, and finally obsolete ontologies.

Each column after the ontology ID represents one dashboard check. There are four levels of results for each column:

1. Pass - green check
2. Info - blue *i*
3. Warning - yellow exclamation point
4. Error - red **x**

For details on what constitutes a pass versus an error for each check, click on the column header.

The last column contains a summary of the dashboard check. This column corresponds to the lowest result of all checks. For example, if there are any errors, this column will contain a red **x**. Likewise, if there are any infos, but no errors or warnings, this column will contain a blue *i*.

Finally, you can download the report summary as a YAML file from the link near the top of the page.

---

## Reading Individual Results

To view more details on an ontology's results, click on the ontology ID in the first column.

From the dashboard report page, you can see the version IRI that the dashboard was run on (for all OWL file checks) and the date it was run. Some checks include reports, which you can view under the **Resources** column. Each individual report page includes a link to download those reports as TSV files.

#### Reading ROBOT Reports

[ROBOT report](http://robot.obolibrary.org/report) runs a series of standard queries over the OWL file. More details on these queries can be [found here](http://robot.obolibrary.org/report_queries/). Like the dashboard checks, report has three levels of violations (passing results are not shown in the table): info, warning, and error.

Each row contains the violation level, the rule name (corresponding to a query), the subject of the violation, the property of the violation, and the value of the violation. For specific details on what the rule checks and how to fix it, click on the rule name.

---
