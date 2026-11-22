import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

CBIO = "https://www.cbioportal.org/api"
ENTREZ = {"ERBB2": 2064, "ESR1": 2099, "EGFR": 1956, "PIK3CA": 5290, "PTEN": 5728, "MET": 4233,
          "IGF1R": 3480, "CCND1": 595, "RB1": 5925}
STUDY = {"HER2": "brca_tcga_pan_can_atlas_2018", "ER": "brca_tcga_pan_can_atlas_2018",
         "EGFR": "luad_tcga_pan_can_atlas_2018"}
EVIDENCE_WIDTH = {"Clinical": 3, "Preclinical": 1}
COLUMN_COLORS = ["#1565c0", "#ef6c00", "#7b1fa2", "#2e7d32"]


@st.cache_data
def load():
    return pd.read_csv("data/resistance.csv"), pd.read_csv("data/resistance_markers.csv")


# ---------------- cBioPortal helpers ----------------
@st.cache_data(show_spinner=False)
def all_samples(study):
    return set(requests.get(f"{CBIO}/sample-lists/{study}_all", timeout=30).json()["sampleIds"])


@st.cache_data(show_spinner=False)
def altered(gene, study, kind):
    """Samples with AMP (amplified), HOMDEL (deleted) or MUT (mutated) gene."""
    body = {"sampleListId": f"{study}_all", "entrezGeneIds": [ENTREZ[gene]]}
    if kind in ("AMP", "HOMDEL"):
        rows = requests.post(f"{CBIO}/molecular-profiles/{study}_gistic/discrete-copy-number/fetch",
                             json=body, params={"discreteCopyNumberEventType": kind}, timeout=60).json()
    else:
        rows = requests.post(f"{CBIO}/molecular-profiles/{study}_mutations/mutations/fetch",
                             json=body, timeout=60).json()
    return {r["sampleId"] for r in rows}


@st.cache_data(show_spinner=False)
def er_high(study):
    """ER-positive-like tumours: ESR1 mRNA above the 30th percentile (about 70% of breast cancers are ER+)."""
    rows = requests.post(f"{CBIO}/molecular-profiles/{study}_rna_seq_v2_mrna/molecular-data/fetch",
                         json={"sampleListId": f"{study}_all", "entrezGeneIds": [ENTREZ["ESR1"]]}, timeout=60).json()
    e = pd.Series({r["sampleId"]: r["value"] for r in rows})
    return set(e[e > e.quantile(0.30)].index)


@st.cache_data(show_spinner="Checking resistance markers in TCGA patients…")
def baseline_markers(receptor, markers):
    study = STUDY[receptor]
    samples = all_samples(study)
    if receptor == "HER2":
        group, label = altered("ERBB2", study, "AMP"), "HER2-amplified tumours"
    elif receptor == "EGFR":
        group, label = altered("EGFR", study, "MUT"), "EGFR-mutant tumours"
    else:
        group, label = er_high(study), "ER-positive-like tumours"
    group &= samples
    rest = samples - group
    rows, carriers = [], set()
    for _, m in markers.iterrows():
        hit = set()
        for kind in m["alteration_kind"].split("|"):
            hit |= altered(m["marker_gene"], study, kind)
        hit &= samples
        carriers |= hit & group
        rows.append({"Resistance marker": m["marker_label"],
                     f"% of {label}": round(100 * len(hit & group) / len(group), 1),
                     "% of other tumours": round(100 * len(hit & rest) / len(rest), 1),
                     "Mechanism": m["linked_mechanism"], "Rescue option": m["rescue_strategy"],
                     "Evidence": m["evidence_level"]})
    return label, len(group), round(100 * len(carriers) / len(group), 1), pd.DataFrame(rows)


# ---------------- Sankey ----------------
def sankey(rows, drug):
    labels, index, colors = [], {}, []

    def node(col, name):
        key = (col, name)
        if key not in index:
            index[key] = len(labels)
            labels.append(name)
            colors.append(COLUMN_COLORS[col])
        return index[key]

    src, tgt, val, lc = [], [], [], []
    for _, r in rows.iterrows():
        w = EVIDENCE_WIDTH.get(r["evidence_level"], 1)
        colour = "rgba(46,125,50,0.45)" if r["evidence_level"] == "Clinical" else "rgba(120,144,156,0.35)"
        path = [node(0, drug), node(1, r["resistance_mechanism"]),
                node(2, r["bypass_target"] if r["bypass_target"] != "None" else "No bypass receptor"),
                node(3, r["rescue_strategy"])]
        for a, b in zip(path, path[1:]):
            src.append(a); tgt.append(b); val.append(w); lc.append(colour)
    fig = go.Figure(go.Sankey(node=dict(label=labels, color=colors, pad=18, thickness=18),
                              link=dict(source=src, target=tgt, value=val, color=lc)))
    fig.update_layout(height=140 + 70 * len(rows), margin=dict(t=30, b=10), font=dict(size=12))
    for i, t in enumerate(["Drug", "Resistance mechanism", "Bypass receptor / pathway", "Rescue option"]):
        fig.add_annotation(x=i / 3, y=1.06, xref="paper", yref="paper", text=f"<b>{t}</b>", showarrow=False)
    return fig


def show_resistance():
    st.title("Resistance → Rescue")
    st.caption("Traces why a receptor-targeted drug stops working and what can be used next "
               "(published evidence; patient data from cBioPortal TCGA)")
    res, markers = load()

    # ================= USER INPUT =================
    with st.container(border=True):
        st.markdown("#### Input")
        a, b, c = st.columns(3)
        receptor = a.selectbox("Receptor", sorted(res["receptor"].unique()))
        # drugs with the most documented pathways first
        drugs = res.loc[res["receptor"] == receptor, "drug"].value_counts().index.tolist()
        drug = b.selectbox("Drug that stopped working", drugs, key=f"drug_{receptor}")
        evidence = c.multiselect("Evidence level", ["Clinical", "Preclinical"], default=["Clinical", "Preclinical"])
        check_patients = st.checkbox("Also check how many TCGA patients already carry these resistance markers",
                                     value=True)
        go_btn = st.button("Analyse", type="primary", key="analyse_resistance")

    if go_btn:
        if not evidence:
            st.error("Choose at least one evidence level.")
            return
        rows = res[(res["drug"] == drug) & (res["evidence_level"].isin(evidence))]
        patients = None
        if check_patients:
            try:
                patients = baseline_markers(receptor, markers[markers["receptor"] == receptor])
            except Exception as e:
                st.warning(f"Could not fetch patient data: {e}")
        st.session_state["resistance_result"] = {"receptor": receptor, "drug": drug, "rows": rows,
                                                 "patients": patients}

    if "resistance_result" not in st.session_state:
        st.info("Choose the input above and click **Analyse** to see the resistance pathways.")
        return

    # ================= RESULTS =================
    out = st.session_state["resistance_result"]
    rows, drug = out["rows"], out["drug"]
    st.markdown(f"### Results: {drug} ({out['receptor']})")
    if rows.empty:
        st.warning("No resistance pathway in the dataset for this drug and evidence level.")
        return

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Resistance mechanisms", len(rows))
    k2.metric("With clinical evidence", int((rows["evidence_level"] == "Clinical").sum()))
    k3.metric("Rescue options", rows["rescue_strategy"].nunique())
    if out["patients"]:
        label, n, pct, _ = out["patients"]
        k4.metric("Patients with a marker before treatment", f"{pct}%", f"of {n} {label}", delta_color="off")

    with st.container(border=True):
        st.markdown("**Resistance → rescue map**")
        st.plotly_chart(sankey(rows, drug), width="stretch")
        st.caption("Green flows = clinical evidence (thicker); grey flows = preclinical evidence (thinner).")

    st.dataframe(rows.drop(columns=["drug", "receptor"]).rename(columns=lambda c: c.replace("_", " ").capitalize()),
                 hide_index=True, width="stretch")

    if out["patients"]:
        label, n, pct, table = out["patients"]
        with st.container(border=True):
            st.markdown(f"**Resistance markers already present before treatment: {pct}% of {n} {label}**")
            col = [c for c in table.columns if c.startswith("% of ") and "other" not in c][0]
            long = table.melt(id_vars="Resistance marker", value_vars=[col, "% of other tumours"],
                              var_name="Group", value_name="% of patients")
            fig = px.bar(long, x="% of patients", y="Resistance marker", color="Group", barmode="group",
                         orientation="h", text="% of patients", color_discrete_sequence=["#c2185b", "#90a4ae"])
            fig.update_layout(height=120 + 55 * len(table), margin=dict(t=10, b=10), legend_title_text="")
            st.plotly_chart(fig, width="stretch")
            st.dataframe(table, hide_index=True, width="stretch")
            st.caption("Patients who already carry a marker are at higher risk that this therapy alone will fail.")

    st.download_button("Download pathways (CSV)", rows.to_csv(index=False),
                       file_name=f"resistance_{drug}.csv", mime="text/csv")
