import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="ReceptorRx", page_icon="🧬", layout="wide")

# ---------------- one input: the patient's receptor profile ----------------
PROFILES = {
    "Breast cancer – HER2-positive": {
        "receptor": "HER2", "prevalence": "11.3% of breast cancers (HER2 amplified, 123 of 1,084 TCGA patients)",
        "first": ["HER2_MAB"], "next": ["HER2_TDXD", "HER2_TDM1", "HER2_TUC", "HER2_LAP"],
        "guide_first": "HER2_MAB", "guide_next": "HER2_TDXD", "resist_drugs": ["Trastuzumab", "T-DM1"]},
    "Breast cancer – ER-positive, HER2-negative": {
        "receptor": "ER", "prevalence": "About 70% of breast cancers are ER-positive (hormone-receptor positive)",
        "first": ["ER_AI_CDK", "ER_FUL", "ER_TAM"], "next": ["ER_ELA"],
        "guide_first": "ER_AI_CDK", "guide_next": "ER_ELA", "resist_drugs": ["Aromatase inhibitor", "CDK4/6 inhibitor"]},
    "Lung cancer – EGFR-mutant": {
        "receptor": "EGFR", "prevalence": "12.4% of lung adenocarcinomas (EGFR mutated, 70 of 566 TCGA patients)",
        "first": ["EGFR_OSI", "EGFR_GEF", "EGFR_AMI"], "next": [],
        "guide_first": "EGFR_OSI", "guide_next": None, "resist_drugs": ["Osimertinib", "Gefitinib or erlotinib"]},
    "Breast cancer – Triple-negative": {"receptor": None},
}

# weights used to combine trial results into one score (out of 100)
W = {"efficacy": 3, "durability": 3, "safety": 2, "cost": 1, "convenience": 1}
COST = {"Generic oral": 5, "Generic injection": 4, "Branded oral": 3, "Branded oral + biologic": 2,
        "Branded biologic": 2, "ADC or bispecific": 1}
ROUTE = {"Oral daily": 5, "Oral daily + oral chemo": 4, "IM injection monthly": 3, "IV every 3 weeks": 3,
         "IV every 3 weeks + oral": 2, "IV every 3 weeks + chemo": 2, "IV every 2 weeks + oral": 1}


@st.cache_data
def load():
    res = pd.read_csv("data/resistance.csv")
    res["bypass_target"] = res["bypass_target"].fillna("None")
    return (pd.read_csv("data/receptors.csv"), pd.read_csv("data/drugs.csv"),
            pd.read_csv("data/strategy_scores.csv"), res)


def score(df):
    """Turn published trial results into a score out of 100."""
    s = df.copy()
    s["efficacy"] = df["orr_pct"].apply(lambda x: 1 + 4 * x / 100).fillna(df["efficacy"])
    s["durability"] = df["pfs_months"].apply(lambda x: 1 + 4 * min(x, 30) / 30).fillna(df["durability"])
    s["safety"] = df["grade3_ae_pct"].apply(lambda x: 5 - 4 * x / 100).fillna(df["safety"])
    s["cost"] = df["cost_tier"].map(COST).fillna(df["cost"])
    s["convenience"] = df["route"].map(ROUTE).fillna(df["convenience"])
    s["Score"] = (sum(W[c] * s[c] for c in W) / (5 * sum(W.values())) * 100).round(1)
    return s.sort_values("Score", ascending=False)


receptors, drugs, strategies, resistance = load()

# ================= INPUT =================
st.title("🧬 ReceptorRx")
st.markdown("**Evaluation of Receptor-Targeted Therapeutic Strategies for Cancer Treatment**  \n"
            "Choose a tumour's receptor profile to see its receptor, the drugs that target it, "
            "which strategy works best, and what to use if it stops working.")

c1, c2 = st.columns([3, 1])
choice = c1.selectbox("Tumour receptor profile", list(PROFILES.keys()), label_visibility="collapsed")
if c2.button("Analyse", type="primary", width="stretch"):
    st.session_state["choice"] = choice
if "choice" not in st.session_state:
    st.info("Choose a receptor profile and click **Analyse**.")
    st.stop()

p = PROFILES[st.session_state["choice"]]
st.divider()
st.header(st.session_state["choice"])

if p["receptor"] is None:
    st.warning("Triple-negative breast cancer has **no HER2, ER or PR receptor** to target, so receptor-targeted "
               "therapies in this platform do not apply. Treatment is usually chemotherapy or immunotherapy.")
    st.stop()

rec = receptors[receptors["receptor"] == p["receptor"]].iloc[0]
rec_drugs = drugs[drugs["receptor"] == p["receptor"]].sort_values("fda_year")
ranked = score(strategies[strategies["strategy_id"].isin(p["first"] + p["next"])])
ranked["Line"] = ranked["strategy_id"].apply(lambda s: "First line" if s in p["first"] else "After progression")
best = ranked[ranked["Line"] == "First line"].iloc[0]
nxt = ranked[ranked["Line"] == "After progression"]
res_rows = resistance[resistance["drug"].isin(p["resist_drugs"])]

# ================= KEY RESULTS =================
k1, k2, k3 = st.columns(3)
k1.metric("Target receptor", f"{rec['receptor']} ({rec['gene']})")
k2.metric("Drugs that target it", len(rec_drugs))
k3.markdown(f"Best first-line strategy  \n**{best['strategy'].split(' (')[0]}**  \nscore {best['Score']}/100")

# ---------- 1. Receptor ----------
st.subheader("1 · The receptor")
with st.container(border=True):
    st.write(f"**{rec['protein_name']}** · {rec['receptor_type']} · located in the **{rec['cell_location'].lower()}**")
    st.write(f"**Role:** {rec['function']}")
    st.write(f"**How common:** {p['prevalence']}")
    st.write(f"**How it is tested:** {rec['biomarker_test']}")
    st.caption(f"Sources: NCBI Gene {rec['ncbi_gene_id']} · UniProt {rec['uniprot_id']} · cBioPortal (TCGA)")

# ---------- 2. Drugs ----------
st.subheader(f"2 · Drugs that target {rec['receptor']}")
st.dataframe(rec_drugs[["drug", "drug_class", "mechanism", "route", "fda_year"]].rename(columns={
    "drug": "Drug", "drug_class": "Type", "mechanism": "How it works", "route": "Given as", "fda_year": "FDA approved"}),
    hide_index=True, width="stretch")
st.caption("Sources: ChEMBL, Drugs@FDA")

# ---------- 3. Which works best ----------
st.subheader("3 · Which strategy works best?")
fig = px.bar(ranked.iloc[::-1], x="Score", y="strategy", color="Line", orientation="h", text="Score",
             color_discrete_map={"First line": "#1565c0", "After progression": "#ef6c00"},
             labels={"strategy": "", "Score": "Score out of 100"})
fig.update_layout(height=110 + 50 * len(ranked), xaxis_range=[0, 100], margin=dict(t=10, b=10), legend_title_text="")
st.plotly_chart(fig, width="stretch")
msg = f"✅ **Recommended first:** {best['strategy']} ({best['Score']}/100)"
if best["strategy_id"] == p["guide_first"]:
    msg += " — agrees with NCCN/ESMO guidelines"
if not nxt.empty:
    n = nxt.iloc[0]
    msg += f"  \n➡️ **If the cancer progresses:** {n['strategy']} ({n['Score']}/100)"
    if n["strategy_id"] == p["guide_next"]:
        msg += " — agrees with guidelines"
st.success(msg)
st.dataframe(ranked[["strategy", "Line", "orr_pct", "pfs_months", "grade3_ae_pct", "Score", "trial"]].rename(columns={
    "strategy": "Strategy", "orr_pct": "Tumour response (%)", "pfs_months": "Months without progression",
    "grade3_ae_pct": "Serious side effects (%)", "trial": "Clinical trial"}), hide_index=True, width="stretch")
st.caption("Score combines tumour response, months without progression, serious side effects, cost and "
           "convenience from phase 3 trials (PubMed). Weights: response 3, progression-free time 3, safety 2, "
           "cost 1, convenience 1.")

# ---------- 4. If it stops working ----------
st.subheader("4 · If the drug stops working")
st.dataframe(res_rows[["drug", "resistance_mechanism", "rescue_strategy", "evidence_level"]].rename(columns={
    "drug": "Drug", "resistance_mechanism": "Why it stops working", "rescue_strategy": "What to try next",
    "evidence_level": "Evidence"}), hide_index=True, width="stretch")
st.caption("Sources: CIViC, PubMed")

st.divider()
st.caption("ReceptorRx integrates NCBI Gene, UniProt, cBioPortal (TCGA), ChEMBL, Drugs@FDA, PubMed and CIViC. "
           "For education and research only — not for clinical decisions.")
