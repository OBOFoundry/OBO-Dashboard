"""
This script generates the analysis.html file for the dashboard.
It processes the data and prepares it for analysis.
It generates plots and tables for the analysis.
"""
import sys
from argparse import ArgumentParser

import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from jinja2 import Template
from lib import load_yaml


def extract_number(data, metric, submetric=None):
    """
    This function extracts the number for the given metric from the data.
    """
    if submetric:
        return (
            [
                o["metrics"][metric][submetric]
                if "metrics" in o
                and metric in o["metrics"]
                and submetric in o["metrics"][metric]
                else 0 for o in data["ontologies"]
            ]
        )

    return (
        [
            o["metrics"][metric]
            if "metrics" in o
            and metric in o["metrics"]
            else 0 for o in data["ontologies"]
        ]
    )


def plot_bar(df, feature, logx=True):
    """
    This function generates a bar plot for the given feature.
    """
    df.sort_values(by=feature, inplace=True)
    height = 300+(len(df)*10)
    fig = px.bar(
        df,
        y="ontology",
        x=feature,
        orientation="h",
        width=800,
        height=height,
        log_x=logx)

    fig.update_layout(
        yaxis={"title": "Ontology", "tickmode": "linear"}
    )

    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def plot_status(df):
    """
    This function generates a bar plot for the status of the ontologies.
    """
    height = 300+(len(df)*10)
    color_map_errors = {
        "PASS": "#c3e6cb",
        "INFO": "#bee5eb",
        "WARN": "#ffeeba",
        "ERROR": "#f5c6cb"
    }
    fig = px.bar(df,
                 y="check",
                 x="value",
                 labels={
                     "check": "OBO Principle",
                     "value": "Number of ontologies"
                 },
                 color="status",
                 orientation="h",
                 width=800,
                 height=height,
                 color_discrete_map=color_map_errors
                 )
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def prep_data(data):
    """
    This function processes the data to prepare it for analysis.
    """
    m_onts = [o["namespace"] for o in data["ontologies"]]
    m_syntax = [
        o["metrics"]["Info: Syntax"]
        if "metrics" in o
        and "Info: Syntax" in o["metrics"]
        else "unknown" for o in data["ontologies"]
    ]

    df = pd.DataFrame({
        "ontology": m_onts,
        "axioms": extract_number(data, "Axioms: Number of axioms"),
        "classes": extract_number(data, "Entities: Number of classes"),
        "entities_reused": extract_number(
            data, "Entities: % of entities reused"
        ),
        "uses": extract_number(data, "Info: How many ontologies use it?"),
        "score": extract_number(
            data, "Info: Experimental OBO score", "oboscore"
        ),
        "score_dash": extract_number(
            data, "Info: Experimental OBO score", "_dashboard"
        ),
        # "score_reuse": extract_number(
        #   data,"Info: Experimental OBO score","_reuse"
        # ),
        "score_impact": extract_number(
            data, "Info: Experimental OBO score", "_impact"
        ),
        # "score_impact_external": extract_number(
        #   data,"Info: Experimental OBO score",
        #   "_impact_external"),
        "syntax": m_syntax
    })

    return df


def table_breakdown(df_all, col_prefix):
    """
    This function generates a table with the breakdown of the data.
    """
    df_axiom_types = df_all[
        [col for col in df_all if col.startswith(col_prefix)]
    ].copy()
    df_axiom_types["o"] = df_all["namespace"]
    df_axiom_types.columns = [
        col.replace(col_prefix, "") for col in df_axiom_types
    ]
    df_axiom_types.fillna(0, inplace=True)
    dt_info = df_axiom_types.describe().T
    dt_info["count"] = df_axiom_types.astype(bool).sum(axis=0)
    dt_info.sort_values(by="count", inplace=True, ascending=False)
    return dt_info.to_html(
        classes="table table-striped table-hover thead-light"
    )


def data_to_plot_status(data):
    """
    This function processes the data to prepare it for plotting.
    It aggregates the data by "check" and "status", and then reshapes the data
    for plotting.
    """
    # Initialize an empty list to store the results
    filtered_results = []

    # Iterate over the ontologies in the data
    for ontology in data["ontologies"]:
        # Check if "results" key exists in the ontology
        if "results" in ontology:
            # Iterate over the results
            for result in ontology["results"]:
                # Check if the result starts with "FP"
                if result.startswith("FP"):
                    # Append the relevant data to the list
                    filtered_results.append(
                        [ontology["namespace"],
                         result,
                         ontology["results"][result]["status"]]
                    )

    # Convert the list to a DataFrame
    results_df = pd.DataFrame(
        filtered_results, columns=["ontology", "check", "status"]
    )

    # Aggregate the data by "check" and "status"
    aggregated_df = results_df.groupby(
        ["check", "status"]
    ).size().reset_index(name="count")

    # Pivot the DataFrame to have "status" as columns
    pivoted_df = aggregated_df.pivot(
        index="check", columns="status", values="count"
    ).reset_index().fillna(0)

    # Define the list of valid status categories
    errcats = ["ERROR", "INFO", "WARN", "PASS"]

    # Check if the status categories exist in the DataFrame
    value_vars = [status for status in errcats if status in pivoted_df.columns]

    # Melt the DataFrame to have "status" and "count" as separate columns
    melted_df = pd.melt(
        pivoted_df,
        id_vars="check",
        value_vars=value_vars
    )

    # Convert "value" to int and "status" to category
    melted_df["value"] = melted_df["value"].astype(int)
    melted_df["status"] = melted_df["status"].astype("category")

    # Reorder the categories and sort the DataFrame
    melted_df["status"] = melted_df["status"].cat.reorder_categories(
        value_vars
    )
    melted_df.sort_values(["check", "status"], ascending=False, inplace=True)

    return melted_df


def graph_to_plot_dependency(data):
    """
    This function processes the data to prepare it for plotting.
    It extracts the dependencies between the ontologies and
    creates a directed graph.
    """
    dependencies = {}
    for o in data["ontologies"]:
        if "metrics" in o:
            if "Info: Which ontologies use it?" in o["metrics"]:
                dependencies[o["namespace"]] = (
                    o["metrics"]["Info: Which ontologies use it?"]
                )

    graph = nx.DiGraph()

    for ontology, list_dep in dependencies.items():
        if len(list_dep) > 1:
            for dep in list_dep:
                graph.add_edge(ontology, dep)

    edge_x = []
    edge_y = []

    pos = nx.kamada_kawai_layout(graph)

    for edge in graph.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.append(x0)
        edge_x.append(x1)
        edge_x.append(None)
        edge_y.append(y0)
        edge_y.append(y1)
        edge_y.append(None)

    node_x = []
    node_y = []
    node_count = len(graph.nodes())
    for node in graph.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

    node_adjacencies = []
    node_sizes = []
    node_text = []
    for node, adjacencies in enumerate(graph.adjacency()):
        node_adjacencies.append(len(adjacencies[1]))
        uses = len(adjacencies[1])
        node_text.append(f"{adjacencies[0]} ({uses} uses)")
        node_sizes.append((20*uses)/node_count+10)

    return (
        edge_x, edge_y, node_x, node_y, node_sizes, node_adjacencies, node_text
    )


def plot_graph_dependency(
    edge_x, edge_y, node_x, node_y, node_sizes, node_adjacencies, node_text
):
    """
    This function generates a plot of the dependency graph.
    """
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line={"width": 0.5, "color": "#888"},
        hoverinfo="none",
        mode="lines"
    )
    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers",
        hoverinfo="text",
        marker={
            "showscale": True,
            # colorscale options
            # "Greys" | "YlGnBu" | "Greens" | "YlOrRd" | "Bluered" | "RdBu" |
            # "Reds" | "Blues" | "Picnic" | "Rainbow" | "Portland" | "Jet" |
            # "Hot" | "Blackbody" | "Earth" | "Electric" | "Viridis" |
            "colorscale": "YlGnBu",
            "reversescale": True,
            "color": [],
            "size": node_sizes,
            "colorbar": {
                "thickness": 15,
                "title": "Node Connections",
                "xanchor": "left",
                "titleside": "right"
            },
            "line_width": 2
        }
    )
    node_trace.marker.color = node_adjacencies
    node_trace.text = node_text
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            showlegend=False,
            hovermode="closest",
            margin={"b": 20, "l": 5, "r": 5, "t": 40},
            xaxis={
                "showgrid": False, "zeroline": False, "showticklabels": False
            },
            yaxis={
                "showgrid": False, "zeroline": False, "showticklabels": False
            }
        )
    )
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def main(args):
    """
    This function generates the analysis.html file for the dashboard.
    """
    parser = ArgumentParser(
        description="Generate the analysis.html file for the dashboard"
    )
    parser.add_argument(
        "--dashboard-results",
        dest="dashboard_results",
        type=str,
        help="Path to the dashboard results file",
        required=True
    )
    parser.add_argument(
        "--template",
        dest="template",
        type=str,
        help="Path to the Jinja2 template file",
        required=True
    )
    parser.add_argument(
        "--output",
        dest="output",
        type=str,
        help="Path to the output HTML file",
        required=True
    )
    args = parser.parse_args()

    dash_results = load_yaml(args.dashboard_results)
    df = prep_data(dash_results)
    df_all = pd.json_normalize(dash_results["ontologies"])
    df_score = df[["ontology", "score", "score_dash", "score_impact"]].copy()
    df_score.sort_values("score", inplace=True, ascending=False)

    with open(args.template, mode="r", encoding="utf-8") as f:
        template = Template(f.read())

    rendered_template = template.render(
        title="Dashboard Analysis",
        description="Analysis of the ontologies in the dashboard",
        plot_ontologies_status=plot_status(
            data_to_plot_status(dash_results)
        ),
        plot_ontologies_by_axioms=plot_bar(df, "axioms"),
        plot_ontologies_by_classes=plot_bar(df, "classes"),
        plot_ontologies_by_usage=plot_bar(df, "uses"),
        table_serialisations=(
            df["syntax"].value_counts().to_frame().T
            .to_html(classes="table table-striped table-hover thead-dark")
        ),
        table_axiom_types=table_breakdown(
            df_all, "metrics.Axioms: Breakdown of axiom types."),
        table_class_expressions=table_breakdown(
            df_all, "metrics.Info: Breakdown of OWL class expressions used."
        ),
        table_obo_score=(
            df_score.to_html(
                classes="table table-striped table-hover thead-light"
            )
        ),
        table_obo_score_summary=(
            df_score.describe().T
            .to_html(classes="table table-striped table-hover thead-light")
        ),
        plot_obo_dependency_graph=(
            plot_graph_dependency(*graph_to_plot_dependency(dash_results))
        )
    )

    with open(args.output, mode="w", encoding="utf-8") as f:
        f.write(rendered_template)


if __name__ == "__main__":
    main(sys.argv)
