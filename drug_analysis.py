import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

CLASS_COLORS = {
    "Monoclonal antibody": "#1565c0",
    "Antibody-drug conjugate": "#7b1fa2",
    "Kinase inhibitor": "#ef6c00",
    "Bispecific antibody": "#c2185b",
    "Hormonal therapy (SERM)": "#26a69a",
    "Hormonal therapy (SERD)": "#00897b",
    "Aromatase inhibitor": "#8d6e63",
}


@st.cache_data
def load_drugs():
    return pd.read_csv("data/drugs.csv")


def network_figure(receptor, d):
    """Receptor in the centre, drug classes around it, drugs around each class."""
    G = nx.Graph()
    G.add_node(receptor, kind="receptor")
    for cls in d["drug_class"].unique():
        G.add_node(cls, kind="class")
        G.add_edge(receptor, cls)
    for _, r in d.iterrows():
        G.add_node(r["drug"], kind="drug", cls=r["drug_class"], info=r["mechanism"])
        G.add_edge(r["drug_class"], r["drug"])
    pos = nx.spring_layout(G, seed=7, k=0.9)

    fig = go.Figure()
    for a, b in G.edges():
        fig.add_trace(go.Scatter(x=[pos[a][0], pos[b][0]], y=[pos[a][1], pos[b][1]], mode="lines",
                                 line=dict(color="#b0bec5", width=1.5), hoverinfo="skip", showlegend=False))
    for kind, size in (("class", 30), ("drug", 16)):
        nodes = [n for n, k in G.nodes(data="kind") if k == kind]
        colors = [CLASS_COLORS.get(n if kind == "class" else G.nodes[n]["cls"], "#607d8b") for n in nodes]
        hover = [n if kind == "class" else f"{n}<br>{G.nodes[n]['info']}" for n in nodes]
        fig.add_trace(go.Scatter(x=[pos[n][0] for n in nodes], y=[pos[n][1] for n in nodes],
                                 mode="markers+text", text=nodes, textposition="top center",
                                 hovertext=hover, hoverinfo="text", showlegend=False,
                                 marker=dict(size=size, color=colors, line=dict(color="white", width=1.5))))
    fig.add_trace(go.Scatter(x=[pos[receptor][0]], y=[pos[receptor][1]], mode="markers+text",
                             text=[f"<b>{receptor}</b>"], textfont=dict(color="white", size=14),
                             marker=dict(size=60, color="#0d47a1"), hoverinfo="skip", showlegend=False))
    fig.update_layout(height=560, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="white",
                      xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig


def show_drugs():
    st.title("Receptor-Targeted Drug Analysis")
    st.caption("Sources: ChEMBL (mechanism of action), Drugs@FDA (approval year)")

    df = load_drugs()

    # ================= USER INPUT =================
    with st.container(border=True):
        st.markdown("#### Input")
        c1, c2, c3 = st.columns(3)
        receptor = c1.selectbox("Receptor", sorted(df["receptor"].unique()))
        classes = sorted(df.loc[df["receptor"] == receptor, "drug_class"].unique())
        chosen = c2.multiselect("Drug classes", classes, default=classes, key=f"cls_{receptor}")
        years = c3.slider("FDA approval between", 1975, 2026, (1975, 2026))
        go_btn = st.button("Analyse", type="primary", key="analyse_drugs")

    if go_btn:
        if not chosen:
            st.error("Choose at least one drug class.")
            return
        d = df[(df["receptor"] == receptor) & (df["drug_class"].isin(chosen)) &
               (df["fda_year"].between(years[0], years[1]))].sort_values("fda_year")
        st.session_state["drug_result"] = {"receptor": receptor, "d": d}

    if "drug_result" not in st.session_state:
        st.info("Choose the input above and click **Analyse** to see the results.")
        return

    # ================= RESULTS =================
    receptor, d = st.session_state["drug_result"]["receptor"], st.session_state["drug_result"]["d"]
    if d.empty:
        st.warning("No drugs match this input. Widen the classes or years.")
        return
    st.markdown(f"### Results: drugs targeting {receptor}")

    # ---------- Summary numbers ----------
    c1, c2, c3 = st.columns(3)
    c1.metric("Drugs targeting " + receptor, len(d))
    c2.metric("Drug classes", d["drug_class"].nunique())
    c3.metric("First FDA approval", int(d["fda_year"].min()))

    # ---------- Network + drug details ----------
    left, right = st.columns([1.6, 1])
    with left, st.container(border=True):
        st.markdown("**Drug–receptor network**")
        st.plotly_chart(network_figure(receptor, d), width="stretch")
        st.caption("Centre = receptor · middle ring = drug class · outer = drugs. Hover a drug for its mechanism.")
    with right, st.container(border=True):
        pick = st.selectbox("Drug details", list(d["drug"]))
        r = d[d["drug"] == pick].iloc[0]
        st.markdown(f"### {r['drug']}")
        st.caption(f"{r['brand']} · {r['drug_class']}")
        st.write(f"**Mechanism:** {r['mechanism']}")
        st.write(f"**How it is given:** {r['route']}")
        st.write(f"**FDA approval:** {r['fda_year']}")
        st.write(f"**Main use:** {r['main_indication']}")
        name = r["drug"].split(" (")[0]
        st.markdown(f"[ChEMBL](https://www.ebi.ac.uk/chembl/g/#search_results/all/query={name}) · "
                    f"[ClinicalTrials.gov](https://clinicaltrials.gov/search?intr={name}) · "
                    f"[PubMed](https://pubmed.ncbi.nlm.nih.gov/?term={name})")

    # ---------- Classification + timeline ----------
    a, b = st.columns(2)
    with a, st.container(border=True):
        st.markdown("**Drugs by class**")
        counts = d["drug_class"].value_counts().reset_index()
        counts.columns = ["Drug class", "Number of drugs"]
        fig = go.Figure(go.Bar(x=counts["Number of drugs"], y=counts["Drug class"], orientation="h",
                               marker_color=[CLASS_COLORS.get(c, "#607d8b") for c in counts["Drug class"]]))
        fig.update_layout(height=300, margin=dict(t=10, b=10), xaxis_title="Number of drugs")
        st.plotly_chart(fig, width="stretch")
    with b, st.container(border=True):
        st.markdown("**FDA approval timeline**")
        t = d.copy()
        t["label"] = t["drug"].str.split(" \\(").str[0]
        # alternate labels above / below within each class so close years don't overlap
        t["pos"] = t.groupby("drug_class").cumcount().map(lambda i: "top center" if i % 2 == 0 else "bottom center")
        fig = go.Figure(go.Scatter(x=t["fda_year"], y=t["drug_class"], mode="markers+text",
                                   text=t["label"], textposition=t["pos"].tolist(), textfont=dict(size=11),
                                   marker=dict(size=14, color=[CLASS_COLORS.get(c, "#607d8b") for c in t["drug_class"]])))
        fig.update_layout(height=340, margin=dict(t=20, b=10), xaxis_title="Year of FDA approval",
                          xaxis_range=[t["fda_year"].min() - 3, t["fda_year"].max() + 3])
        st.plotly_chart(fig, width="stretch")

    # ---------- Full table ----------
    st.dataframe(d.drop(columns="receptor"), hide_index=True, width="stretch")
    st.download_button("Download drug list (CSV)", d.to_csv(index=False),
                       file_name=f"drugs_{receptor}.csv", mime="text/csv")
