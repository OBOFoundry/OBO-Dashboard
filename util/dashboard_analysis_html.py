import os
import yaml
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx

import plotly.io as pio


def dashboard_results(file_path):
    with open(file_path, mode="r", encoding="utf-8") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    return data


def extract_number(data, metric, submetric=None):
    if submetric:
        return (
            [
                o['metrics'][metric][submetric]
                if 'metrics' in o
                and metric in o['metrics']
                and submetric in o['metrics'][metric]
                else 0 for o in data['ontologies']
            ]
        )

    return (
        [
            o['metrics'][metric]
            if 'metrics' in o
            and metric in o['metrics']
            else 0 for o in data['ontologies']
        ]
    )


def plot_bar(df, feature, logx=True):
    df.sort_values(by=feature, inplace=True)
    height = 300+(len(df)*10)
    fig = px.bar(
        df,
        y="ontology",
        x=feature,
        orientation='h',
        width=800,
        height=height,
        log_x=logx)

    fig.update_layout(yaxis={"title": 'ontology', "tickmode": 'linear'})

    fig.show()


def table_breakdown(df_all, col_prefix):
    df_axiom_types = df_all[[col for col in df_all if (col.startswith(col_prefix))]].copy()
    df_axiom_types['o']=df_all['namespace']  
    df_axiom_types.columns = [col.replace(col_prefix,"") for col in df_axiom_types]
    df_axiom_types.fillna(0,inplace=True)
    dt_info=df_axiom_types.describe().T
    dt_info['count']=df_axiom_types.astype(bool).sum(axis=0)
    dt_info.sort_values(by='count',inplace=True, ascending=False)
    return dt_info


def analysis():
    data = dashboard_results(os.path.join('dashboard','dashboard-results.yml'))
    
    m_onts = [o['namespace'] for o in data['ontologies']]
    m_syntax = [
        o['metrics']['Info: Syntax']
        if 'metrics' in o
        and 'Info: Syntax' in o['metrics']
        else "unknown" for o in data['ontologies']
    ]

    df = pd.DataFrame({
        'ontology': m_onts,
        'axioms': extract_number(data, 'Axioms: Number of axioms'), 
        'classes': extract_number(data, 'Entities: Number of classes'), 
        'entities_reused': extract_number(data, 'Entities: % of entities reused'),
        'uses': extract_number(data, 'Info: How many ontologies use it?'),
        'score': extract_number(data, 'Info: Experimental OBO score', 'oboscore'),
        'score_dash': extract_number(data, 'Info: Experimental OBO score', '_dashboard'),
        # 'score_reuse': extract_number(data,'Info: Experimental OBO score','_reuse'),
        'score_impact': extract_number(data, 'Info: Experimental OBO score', '_impact'),
        # 'score_impact_external': extract_number(data,'Info: Experimental OBO score','_impact_external'),
        'syntax': m_syntax
    })

    df_all = pd.json_normalize(data['ontologies'])

