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

# ================= COLOURS (green + blue) =================
st.markdown("""
<style>
.banner {background: linear-gradient(90deg, #1565c0, #2e9e5b); color: white; padding: 22px 28px;
         border-radius: 14px; margin-bottom: 18px;}
.banner h1 {color: white; margin: 0; font-size: 2.2rem;}
.banner p {color: #eafff2; margin: 4px 0 0 0; font-size: 1.05rem;}
.card {background: #eef6ff; border-left: 6px solid #1565c0; padding: 14px 18px; border-radius: 10px;
       margin-bottom: 12px; color: #0d2b4e;}
.card.green {background: #ecf9f1; border-left-color: #2e9e5b; color: #123d26;}
.card b {color: inherit;}
.kpi {background: linear-gradient(135deg, #1565c0, #2e9e5b); color: white; border-radius: 12px;
      padding: 14px 18px; text-align: center;}
.kpi .v {font-size: 1.6rem; font-weight: 700;}
.kpi .l {font-size: 0.9rem; opacity: 0.9;}
section[data-testid="stSidebar"] {background: linear-gradient(180deg, #e3f0ff, #e6f7ec);}
section[data-testid="stSidebar"] * {color: #0d2b4e !important;}
</style>
""", unsafe_allow_html=True)


def banner(title, sub=""):
    st.markdown(f'<div class="banner"><h1>{title}</h1><p>{sub}</p></div>', unsafe_allow_html=True)


def card(html, green=False):
    st.markdown(f'<div class="card{" green" if green else ""}">{html}</div>', unsafe_allow_html=True)


def kpi(col, value, label):
    col.markdown(f'<div class="kpi"><div class="v">{value}</div><div class="l">{label}</div></div>',
                 unsafe_allow_html=True)


# ================= SIDEBAR: one input + page menu =================
st.sidebar.markdown("## 🧬 ReceptorRx")
choice = st.sidebar.selectbox("Choose the tumour receptor profile", list(PROFILES.keys()))
page = st.sidebar.radio("Go to", ["🏠 Home", "1 · Receptor", "2 · Drugs", "3 · Best strategy",
                                  "4 · If it stops working"])
st.sidebar.caption("For education and research only — not for clinical decisions.")

p = PROFILES[choice]

# ================= HOME =================
if page == "🏠 Home":
    banner("🧬 ReceptorRx", "Evaluation of Receptor-Targeted Therapeutic Strategies for Cancer Treatment")
    card("<b>What is this app?</b><br>Many cancers grow because a <b>receptor</b> on the cancer cell "
         "(like HER2, ER or EGFR) is switched on too much. Drugs that block that receptor are called "
         "<b>receptor-targeted therapies</b>. ReceptorRx helps you see which of these drugs works best for "
         "each receptor type — a simple form of <b>personalised medicine</b>.")
    card("<b>How to use it</b><br>1. Choose a tumour receptor profile in the left menu.<br>"
         "2. Open each page: Receptor → Drugs → Best strategy → If it stops working.", green=True)
    c1, c2, c3, c4 = st.columns(4)
    kpi(c1, "3", "Receptor types<br>HER2 · ER · EGFR")
    kpi(c2, len(drugs), "Approved targeted drugs")
    kpi(c3, len(strategies), "Strategies scored<br>from phase 3 trials")
    kpi(c4, len(resistance), "Resistance mechanisms")
    st.write("")
    card("<b>What each page shows</b><br>"
         "<b>1 · Receptor</b> – what the receptor is, what it does, how common it is (TCGA patients)<br>"
         "<b>2 · Drugs</b> – all approved drugs that target it and how they work<br>"
         "<b>3 · Best strategy</b> – each treatment scored out of 100 from real trial results, checked "
         "against NCCN/ESMO guidelines<br>"
         "<b>4 · If it stops working</b> – why the drug fails (resistance) and what to try next")
    card("<b>Data sources (all public)</b><br>NCBI Gene · UniProt · cBioPortal (TCGA) · ChEMBL · "
         "Drugs@FDA · PubMed (phase 3 trials) · CIViC · NCCN/ESMO guidelines", green=True)
    st.stop()

# ---------- triple-negative: nothing to target ----------
if p["receptor"] is None:
    banner(choice, "No receptor to target")
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
gene = rec["gene"] if rec["gene"] != rec["receptor"] else ""
rec_name = f"{rec['receptor']} ({gene})" if gene else rec["receptor"]

# ================= 1. RECEPTOR =================
if page == "1 · Receptor":
    banner(f"1 · The receptor: {rec_name}", choice)
    c1, c2, c3 = st.columns(3)
    kpi(c1, rec_name, "Target receptor")
    kpi(c2, rec["cell_location"], "Location in cell")
    kpi(c3, p["prevalence"].split(" ")[0] if "%" in p["prevalence"].split(" ")[0] else "~70%", "Patients with it")
    st.write("")
    card(f"<b>{rec['protein_name']}</b> · {rec['receptor_type']}")
    card(f"<b>Role:</b> {rec['function']}", green=True)
    card(f"<b>How common:</b> {p['prevalence']}")
    card(f"<b>How it is tested:</b> {rec['biomarker_test']}", green=True)
    st.caption(f"Sources: NCBI Gene {rec['ncbi_gene_id']} · UniProt {rec['uniprot_id']} · cBioPortal (TCGA)")

# ================= 2. DRUGS =================
elif page == "2 · Drugs":
    banner(f"2 · Drugs that target {rec['receptor']}", f"{len(rec_drugs)} approved drugs")
    fig = px.scatter(rec_drugs, x="fda_year", y="drug", color="drug_class", size=[18] * len(rec_drugs),
                     color_discrete_sequence=["#1565c0", "#2e9e5b", "#00897b", "#42a5f5", "#66bb6a"],
                     labels={"fda_year": "Year FDA approved", "drug": "", "drug_class": "Type"})
    fig.update_layout(height=120 + 45 * len(rec_drugs), margin=dict(t=10, b=10))
    st.plotly_chart(fig, width="stretch")
    st.dataframe(rec_drugs[["drug", "drug_class", "mechanism", "route", "fda_year"]].rename(columns={
        "drug": "Drug", "drug_class": "Type", "mechanism": "How it works", "route": "Given as",
        "fda_year": "FDA approved"}), hide_index=True, width="stretch")
    st.caption("Sources: ChEMBL, Drugs@FDA")

# ================= 3. BEST STRATEGY =================
elif page == "3 · Best strategy":
    banner("3 · Which strategy works best?", choice)
    c1, c2 = st.columns(2)
    kpi(c1, best["strategy"].split(" (")[0], f"Best first-line · {best['Score']}/100")
    if not nxt.empty:
        kpi(c2, nxt.iloc[0]["strategy"].split(" (")[0], f"If it progresses · {nxt.iloc[0]['Score']}/100")
    else:
        kpi(c2, len(ranked), "Strategies compared")
    st.write("")
    fig = px.bar(ranked.iloc[::-1], x="Score", y="strategy", color="Line", orientation="h", text="Score",
                 color_discrete_map={"First line": "#1565c0", "After progression": "#2e9e5b"},
                 labels={"strategy": "", "Score": "Score out of 100"})
    fig.update_layout(height=110 + 50 * len(ranked), xaxis_range=[0, 100], margin=dict(t=10, b=10),
                      legend_title_text="")
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
    st.dataframe(ranked[["strategy", "Line", "orr_pct", "pfs_months", "grade3_ae_pct", "Score", "trial"]].rename(
        columns={"strategy": "Strategy", "orr_pct": "Tumour response (%)",
                 "pfs_months": "Months without progression", "grade3_ae_pct": "Serious side effects (%)",
                 "trial": "Clinical trial"}), hide_index=True, width="stretch")
    card("<b>How the score works</b><br>Each strategy gets 1–5 points for tumour response, months without "
         "progression, safety (fewer serious side effects), cost and convenience, from phase 3 trials. "
         "Weights: response 3, progression-free time 3, safety 2, cost 1, convenience 1. "
         "Total is shown out of 100.", green=True)

# ================= 4. RESISTANCE =================
else:
    banner("4 · If the drug stops working", choice)
    c1, c2 = st.columns(2)
    kpi(c1, len(res_rows), "Resistance mechanisms")
    kpi(c2, int((res_rows["evidence_level"] == "Clinical").sum()), "Backed by clinical evidence")
    st.write("")
    for drug_name, grp in res_rows.groupby("drug", sort=False):
        card(f"<b>{drug_name}</b><br>" + "<br>".join(
            f"• {r.resistance_mechanism} → <b>{r.rescue_strategy}</b> <i>({r.evidence_level})</i>"
            for r in grp.itertuples()), green=drug_name == p["resist_drugs"][-1])
    st.caption("Sources: CIViC, PubMed")
