import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="ReceptorRx", page_icon="🧬", layout="wide")

# ---------- one input: the patient's receptor profile ----------
PROFILES = {
    "Breast cancer – HER2-positive": dict(receptor="HER2", gene="ERBB2", entrez=2064, kind="AMP",
        study="brca_tcga_pan_can_atlas_2018", word="amplified", cohort="breast cancers"),
    "Breast cancer – ER-positive": dict(receptor="ER", gene="ESR1", entrez=2099, kind="MUT",
        study="brca_tcga_pan_can_atlas_2018", word="mutated", cohort="breast cancers"),
    "Lung cancer – EGFR-mutant": dict(receptor="EGFR", gene="EGFR", entrez=1956, kind="MUT",
        study="luad_tcga_pan_can_atlas_2018", word="mutated", cohort="lung adenocarcinomas"),
}
WEIGHTS = {"efficacy": 3, "durability": 3, "safety": 2, "cost": 1, "convenience": 1}
COST = {"Generic oral": 5, "Generic injection": 4, "Branded oral": 3, "Branded oral + biologic": 2,
        "Branded biologic": 2, "ADC or bispecific": 1}
ROUTE = {"Oral daily": 5, "Oral daily + oral chemo": 4, "IM injection monthly": 3, "IV every 3 weeks": 3,
         "IV every 3 weeks + oral": 2, "IV every 3 weeks + chemo": 2, "IV every 2 weeks + oral": 1}
CBIO = "https://www.cbioportal.org/api"


@st.cache_data
def load(name):
    return pd.read_csv(f"data/{name}.csv")


@st.cache_data(show_spinner="Fetching patient data from cBioPortal (TCGA)…")
def tcga_percent(entrez, study, kind):
    """% of TCGA patients with the receptor gene amplified or mutated."""
    samples = set(requests.get(f"{CBIO}/sample-lists/{study}_all", timeout=30).json()["sampleIds"])
    body = {"sampleListId": f"{study}_all", "entrezGeneIds": [entrez]}
    if kind == "AMP":
        rows = requests.post(f"{CBIO}/molecular-profiles/{study}_gistic/discrete-copy-number/fetch",
                             json=body, params={"discreteCopyNumberEventType": "AMP"}, timeout=60).json()
    else:
        rows = requests.post(f"{CBIO}/molecular-profiles/{study}_mutations/mutations/fetch",
                             json=body, timeout=60).json()
    altered = len({r["sampleId"] for r in rows} & samples)
    return altered, len(samples)


def rank_strategies(receptor):
    """Score each strategy (0-100) from its phase 3 trial results."""
    df = load("strategy_scores")
    df = df[df["receptor"] == receptor].copy()
    df["efficacy"] = df["orr_pct"].apply(lambda x: 1 + 4 * x / 100).fillna(df["efficacy"])
    df["durability"] = df["pfs_months"].apply(lambda x: 1 + 4 * min(x, 30) / 30).fillna(df["durability"])
    df["safety"] = df["grade3_ae_pct"].apply(lambda x: 5 - 4 * x / 100).fillna(df["safety"])
    df["cost"] = df["cost_tier"].map(COST).fillna(df["cost"])
    df["convenience"] = df["route"].map(ROUTE).fillna(df["convenience"])
    df["Score"] = (sum(w * df[c] for c, w in WEIGHTS.items()) / (5 * sum(WEIGHTS.values())) * 100).round(1)
    lines = load("eligibility_rules").groupby("strategy_id")["line_of_therapy"].first()
    df["Used in"] = df["strategy_id"].map(lines).str.replace("|", " / ", regex=False) + " line"
    return df.sort_values("Score", ascending=False).reset_index(drop=True)


# ================= INPUT =================
st.title("🧬 ReceptorRx")
st.markdown("**Evaluation of Receptor-Targeted Therapeutic Strategies for Cancer Treatment**  \n"
            "Choose a patient's cancer receptor profile to see the receptor, the drugs that target it, "
            "and which treatment works best according to clinical trial evidence.")

c1, c2 = st.columns([3, 1])
choice = c1.selectbox("Patient's cancer receptor profile", list(PROFILES.keys()))
c2.write(""); c2.write("")
if c2.button("Analyse", type="primary", width="stretch"):
    st.session_state["choice"] = choice
if "choice" not in st.session_state:
    st.info("Choose a receptor profile and click **Analyse**.")
    st.stop()

p = PROFILES[st.session_state["choice"]]
rec = load("receptors").query("receptor == @p['receptor']").iloc[0]
drugs = load("drugs").query("receptor == @p['receptor']").sort_values("fda_year")
ranked = rank_strategies(p["receptor"])
resist = load("resistance").query("receptor == @p['receptor']")
best = ranked.iloc[0]

st.divider()
st.header(st.session_state["choice"])

# ================= 1. RECEPTOR =================
st.subheader("1 · The receptor")
a, b = st.columns([2, 1])
with a:
    st.write(f"**{p['receptor']} ({p['gene']})** — {rec['receptor_type']}, located in the {rec['cell_location'].lower()}.")
    st.write(f"**Function:** {rec['function']}")
    st.write(f"**How patients are tested:** {rec['biomarker_test']}")
    st.caption(f"Sources: NCBI Gene {rec['ncbi_gene_id']} · UniProt {rec['uniprot_id']}")
with b:
    try:
        n_alt, n_all = tcga_percent(p["entrez"], p["study"], p["kind"])
        st.metric(f"{p['gene']} {p['word']} in patients", f"{100 * n_alt / n_all:.1f}%",
                  f"{n_alt} of {n_all:,} TCGA {p['cohort']}", delta_color="off")
        if p["receptor"] == "ER":
            st.caption("ESR1 mutations are rare before treatment; they appear after hormone therapy.")
    except Exception:
        st.caption("Patient data from cBioPortal is unavailable right now.")

# ================= 2. DRUGS =================
st.subheader(f"2 · Drugs that target {p['receptor']}")
st.dataframe(drugs[["drug", "drug_class", "mechanism", "route", "fda_year"]].rename(columns={
    "drug": "Drug", "drug_class": "Type", "mechanism": "How it works", "route": "Given as",
    "fda_year": "FDA approved"}), hide_index=True, width="stretch")
st.caption("Sources: ChEMBL, Drugs@FDA")

# ================= 3. WHICH WORKS BEST =================
st.subheader("3 · Which treatment works best?")
st.success(f"**Best-evaluated strategy: {best['strategy']}** — score {best['Score']}/100 "
           f"({best['Used in'].lower()}, {best['trial']})")
fig = px.bar(ranked.iloc[::-1], x="Score", y="strategy", orientation="h", text="Score",
             color_discrete_sequence=["#1565c0"], labels={"strategy": ""})
fig.update_layout(height=90 + 55 * len(ranked), xaxis_range=[0, 100], margin=dict(t=10, b=10))
st.plotly_chart(fig, width="stretch")
st.dataframe(ranked[["strategy", "Used in", "orr_pct", "pfs_months", "grade3_ae_pct", "Score", "trial"]].rename(columns={
    "strategy": "Strategy", "orr_pct": "Tumour response (%)", "pfs_months": "Time before cancer grows (months)",
    "grade3_ae_pct": "Serious side effects (%)", "trial": "Clinical trial"}), hide_index=True, width="stretch")
st.caption("Score out of 100 from phase 3 trial results: response rate and time before the cancer grows count most, "
           "then serious side effects, cost and convenience. Trials enrolled different patients, so comparisons are approximate.")

# ================= 4. IF IT STOPS WORKING =================
st.subheader("4 · If the treatment stops working")
st.dataframe(resist[["drug", "resistance_mechanism", "rescue_strategy", "evidence_level"]].rename(columns={
    "drug": "Drug", "resistance_mechanism": "Why it stops working", "rescue_strategy": "What to use next",
    "evidence_level": "Evidence"}), hide_index=True, width="stretch")
st.caption("Sources: CIViC, PubMed")

st.divider()
st.caption("ReceptorRx is for education and research only. It is not a clinical decision tool.")
