import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="ReceptorRx", page_icon="🧬", layout="wide")

# ---------------- one input: the patient's receptor profile ----------------
PROFILES = {
    "Breast cancer – HER2-positive": {
        "receptor": "HER2", "prevalence": "11.3% of breast cancers (HER2 amplified, 123 of 1,084 TCGA patients)",
        "first": ["HER2_MAB"], "next": ["HER2_TDXD", "HER2_TDM1", "HER2_TUC", "HER2_LAP"],
        "guide_first": "HER2_MAB", "guide_next": "HER2_TDXD", "resist_drugs": ["Trastuzumab", "T-DM1"]},
    "Breast cancer – ER-positive, HER2-negative": {
        "receptor": "ER", "prevalence": "70.9% of breast cancers are luminal (ER-positive) — LumA 499 + LumB 197 of 981 subtyped TCGA patients",
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


def score(df, weights=None):
    """Turn published trial results into a score out of 100.
    Only numbers reported in the trial are used; a missing number is left out (not guessed)
    and the remaining weights are re-scaled."""
    w = weights or W
    s = df.copy()
    s["efficacy"] = df["orr_pct"].apply(lambda x: 1 + 4 * x / 100)
    s["durability"] = df["pfs_months"].apply(lambda x: 1 + 4 * min(x, 30) / 30)
    s["safety"] = df["grade3_ae_pct"].apply(lambda x: 5 - 4 * x / 100)
    s["cost"] = df["cost_tier"].map(COST)
    s["convenience"] = df["route"].map(ROUTE)
    num = sum(w[c] * s[c].fillna(0) for c in w)
    den = sum(w[c] * s[c].notna() for c in w)
    s["Score"] = (num / (5 * den) * 100).round(1)
    s["Missing"] = s[["efficacy", "durability", "safety"]].isna().apply(
        lambda r: ", ".join(n for n, m in zip(["response", "progression-free time", "side effects"], r) if m)
        or "—", axis=1)
    return s.sort_values("Score", ascending=False)


receptors, drugs, strategies, resistance = load()

# ================= STYLE (soft navy · teal · sage) =================
NAVY, TEAL, SAGE, MUTED = "#1e3a5f", "#2c7a7b", "#5a9e7c", "#6b7c8f"
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, .stTabs {font-family: 'Inter', sans-serif;}
.block-container {padding-top: 1.6rem; max-width: 1200px;}
.hero {background: linear-gradient(120deg, #1e3a5f 0%, #24566b 55%, #2c7a7b 100%); border-radius: 18px;
       padding: 30px 34px; color: #fff; margin-bottom: 8px; position: relative; overflow: hidden;}
.hero:after {content: "🧬"; position: absolute; right: 30px; top: 12px; font-size: 92px; opacity: .14;}
.hero h1 {color: #fff; font-size: 2.3rem; font-weight: 700; margin: 0; padding: 0;}
.hero .t {color: #d6ecea; font-size: 1.05rem; margin-top: 4px;}
.pill {display: inline-block; background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.25);
       color: #fff; border-radius: 30px; padding: 3px 12px; font-size: .82rem; margin: 12px 6px 0 0;}
.box {background: #fff; border: 1px solid #e3eae8; border-radius: 14px; padding: 18px 20px;
      box-shadow: 0 2px 8px rgba(30,58,95,.06); margin-bottom: 14px; color: #263544; height: 100%;}
.box h4 {margin: 0 0 6px 0; color: #1e3a5f; font-size: 1.02rem;}
.box p {margin: 0; color: #4a5a6a; font-size: .93rem; line-height: 1.5;}
.step {text-align: left;}
.step .n {display: inline-block; width: 30px; height: 30px; border-radius: 50%; background: #e4f1ef;
          color: #2c7a7b; font-weight: 700; text-align: center; line-height: 30px; margin-bottom: 8px;}
.stat {background: #fff; border: 1px solid #e3eae8; border-top: 4px solid #2c7a7b; border-radius: 12px;
       padding: 14px 16px; box-shadow: 0 2px 8px rgba(30,58,95,.05); color: #263544;}
.stat.g {border-top-color: #5a9e7c;} .stat.n {border-top-color: #1e3a5f;}
.stat .v {font-size: 1.55rem; font-weight: 700; color: #1e3a5f; line-height: 1.2;}
.stat .l {font-size: .82rem; color: #6b7c8f; margin-top: 2px;}
.badge {display: inline-block; border-radius: 6px; padding: 2px 8px; font-size: .75rem; font-weight: 600;
        margin-right: 4px;}
.b-teal {background: #e4f1ef; color: #22696a;} .b-navy {background: #e6edf5; color: #1e3a5f;}
.b-sage {background: #e9f4ee; color: #3d7a5c;} .b-grey {background: #eef1f4; color: #55657a;}
.win {background: linear-gradient(120deg, #eaf5f1, #e8f0f8); border: 1px solid #cfe3dc; border-radius: 14px;
      padding: 18px 22px; margin: 6px 0 14px 0; color: #263544;}
.win .big {font-size: 1.35rem; font-weight: 700; color: #1e3a5f;}
.sec {color: #1e3a5f; font-weight: 700; font-size: 1.3rem; margin: 6px 0 2px 0;}
.sub {color: #6b7c8f; font-size: .9rem; margin-bottom: 14px;}
.bar {background: #e8eeec; border-radius: 8px; height: 10px; margin-top: 8px;}
.bar div {background: linear-gradient(90deg, #2c7a7b, #5a9e7c); height: 10px; border-radius: 8px;}
.flow {display: flex; align-items: center; gap: 10px; flex-wrap: wrap;}
.flow .a {color: #2c7a7b; font-weight: 700;}
.stTabs [data-baseweb="tab-list"] {gap: 6px; border-bottom: 1px solid #e3eae8;}
.stTabs [data-baseweb="tab"] {font-weight: 600; color: #6b7c8f; padding: 10px 14px;}
.stTabs [aria-selected="true"] {color: #2c7a7b !important;}
.stTabs [data-baseweb="tab-highlight"] {background-color: #2c7a7b;}
</style>
""", unsafe_allow_html=True)


def html(x):
    st.markdown(x, unsafe_allow_html=True)


def stat(col, value, label, kind=""):
    col.markdown(f'<div class="stat {kind}"><div class="v">{value}</div><div class="l">{label}</div></div>',
                 unsafe_allow_html=True)


PALETTE = ["#2c7a7b", "#1e3a5f", "#5a9e7c", "#7fb3c9", "#a7c9a0", "#c9d6df"]

# approximate domain map from UniProt (amino-acid positions) + where each drug acts
DOMAINS = {
    "HER2": {"len": 1255, "parts": [("Signal", 1, 22), ("Extracellular (domains I–IV)", 23, 652),
                                     ("Transmembrane", 653, 675), ("Juxtamembrane", 676, 719),
                                     ("Kinase domain", 720, 987), ("C-terminal tail", 988, 1255)],
             "sites": [("Pertuzumab", 265, "domain II"), ("Trastuzumab · T-DM1 · T-DXd", 560, "domain IV"),
                       ("Lapatinib · Tucatinib · Neratinib", 850, "kinase pocket")]},
    "EGFR": {"len": 1210, "parts": [("Signal", 1, 24), ("Extracellular (domains I–IV)", 25, 645),
                                     ("Transmembrane", 646, 668), ("Juxtamembrane", 669, 711),
                                     ("Kinase domain", 712, 979), ("C-terminal tail", 980, 1210)],
             "sites": [("Cetuximab · Amivantamab", 420, "domain III"),
                       ("Gefitinib · Erlotinib · Afatinib · Osimertinib", 760, "kinase pocket"),
                       ("T790M / C797S resistance", 795, "mutation hotspot")]},
    "ER": {"len": 595, "parts": [("AF-1 domain", 1, 184), ("DNA-binding domain", 185, 250),
                                 ("Hinge", 251, 310), ("Ligand-binding domain", 311, 547),
                                 ("F domain", 548, 595)],
           "sites": [("Tamoxifen · Fulvestrant · Elacestrant", 400, "oestrogen pocket"),
                     ("ESR1 Y537S / D538G resistance", 537, "mutation hotspot")]},
}


def nice(fig, h=320):
    fig.update_layout(height=h, margin=dict(t=30, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter, sans-serif", color="#4a5a6a"),
                      legend=dict(orientation="h", y=-0.12), title_font=dict(size=15, color="#1e3a5f"))
    return fig


def domain_map(r):
    d = DOMAINS[r]
    fig = go.Figure()
    cols = ["#c9d6df", "#7fb3c9", "#1e3a5f", "#a7c9a0", "#2c7a7b", "#c9d6df"]
    for (name, a, b), c in zip(d["parts"], cols):
        fig.add_trace(go.Bar(y=[""], x=[b - a + 1], base=[a], orientation="h", marker_color=c, name=name,
                             width=0.35, hovertemplate=f"{name}: aa {a}–{b}<extra></extra>"))
    for i, (drug, pos, where) in enumerate(d["sites"]):
        y = 0.5 + 0.3 * (i % 3)
        lx = pos + 140 if where == "mutation hotspot" and pos + 200 < d["len"] else pos
        fig.add_annotation(x=pos, y=0.18, ax=lx, ay=y, xref="x", yref="y", axref="x", ayref="y",
                           text=f"<b>{drug}</b><br>{where}", showarrow=True, arrowhead=2, arrowcolor="#c0563b",
                           font=dict(size=11, color="#263544"), bgcolor="rgba(255,255,255,.85)")
    fig.update_xaxes(range=[0, d["len"] + 20], title="Amino-acid position", gridcolor="#e8eeec")
    fig.update_yaxes(range=[-0.4, 1.3], showticklabels=False)
    fig.update_layout(barmode="overlay", showlegend=True)
    nice(fig, 360)
    fig.update_layout(legend=dict(orientation="h", y=-0.45))
    return fig


def section(title, sub):
    html(f'<div class="sec">{title}</div><div class="sub">{sub}</div>')


# ================= HERO + PAGES =================
html('<div class="hero"><h1>ReceptorRx</h1>'
     '<div class="t">Evaluation of Receptor-Targeted Therapeutic Strategies for Cancer Treatment</div>'
     '<span class="pill">HER2 · ER · EGFR</span><span class="pill">Real trial data</span>'
     '<span class="pill">Guideline-checked</span><span class="pill">Personalised medicine</span></div>')

home, t1, t2, t3, t4 = st.tabs(["Home", "1 · Receptor", "2 · Drugs", "3 · Best strategy",
                                 "4 · If it stops working"])

with home:
    st.write("")
    a, b = st.columns([1.15, 1])
    with a:
        html('<div class="box"><h4>What is ReceptorRx?</h4><p>Many cancers grow because a <b>receptor</b> on '
             'the cancer cell — such as HER2, ER or EGFR — is over-active. Drugs that block that receptor are '
             '<b>receptor-targeted therapies</b>. ReceptorRx brings receptor, drug, clinical-trial and '
             'resistance data into one place and shows <b>which strategy works best</b> for each receptor '
             'type.</p></div>')
    with b:
        html('<div class="box"><h4>👉 Choose the tumour receptor profile</h4>'
             '<p>Pick one, then open the pages above.</p></div>')
        choice = st.selectbox("Tumour receptor profile", list(PROFILES.keys()), label_visibility="collapsed")
    st.write("")
    section("How it works", "Four steps, one page each")
    steps = [("Receptor", "What the receptor is, what it does and how many patients have it (TCGA)."),
             ("Drugs", "Every approved drug that targets it, with how it works and when it was approved."),
             ("Best strategy", "Each treatment scored out of 100 from phase 3 trials and checked against guidelines."),
             ("If it stops working", "Why the drug fails (resistance) and what to try next.")]
    for col, (i, (t, d)) in zip(st.columns(4), enumerate(steps, 1)):
        col.markdown(f'<div class="box step"><div class="n">{i}</div><h4>{t}</h4><p>{d}</p></div>',
                     unsafe_allow_html=True)
    st.write("")
    section("In this platform", "All from public databases")
    c = st.columns(4)
    stat(c[0], 3, "Receptor types", "n")
    stat(c[1], len(drugs), "Approved targeted drugs")
    stat(c[2], len(strategies), "Strategies scored from trials", "g")
    stat(c[3], len(resistance), "Resistance mechanisms", "n")
    st.write("")
    section("Key findings from TCGA", "Your own cBioPortal analysis")
    a, b = st.columns(2)
    sub = pd.DataFrame({"Subtype": ["Luminal A (ER+)", "Luminal B (ER+)", "Basal / triple-negative",
                                    "HER2-enriched", "Normal-like"], "Patients": [499, 197, 171, 78, 36]})
    f = px.pie(sub, names="Subtype", values="Patients", hole=0.55, color_discrete_sequence=PALETTE,
               title="Breast cancer subtypes (981 TCGA patients)")
    f.update_traces(textinfo="percent", sort=False)
    a.plotly_chart(nice(f, 340), width="stretch")
    alt = pd.DataFrame({"Receptor": ["ER (breast)", "EGFR (lung)", "HER2 (breast)"],
                        "Patients (%)": [70.9, 12.4, 11.3]})
    f = px.bar(alt, x="Patients (%)", y="Receptor", orientation="h", text="Patients (%)",
               color="Receptor", color_discrete_sequence=[TEAL, NAVY, SAGE],
               title="How many patients have each target receptor", labels={"Receptor": ""})
    f.update_traces(texttemplate="%{text}%", textposition="outside", width=0.55, showlegend=False)
    f.update_xaxes(range=[0, 85], gridcolor="#e8eeec")
    a2 = b.plotly_chart(nice(f, 340), width="stretch")
    st.write("")
    html('<div class="box"><h4>Data sources</h4><p>' + " ".join(
        f'<span class="badge b-{k}">{n}</span>' for n, k in [
            ("NCBI Gene", "navy"), ("UniProt", "teal"), ("cBioPortal · TCGA", "sage"), ("ChEMBL", "navy"),
            ("Drugs@FDA", "teal"), ("PubMed trials", "sage"), ("CIViC", "navy"), ("NCCN / ESMO", "teal")])
         + '</p></div>')
    st.caption("For education and research only — not for clinical decisions.")

p = PROFILES[choice]

if p["receptor"] is None:
    for t in (t1, t2, t3, t4):
        with t:
            st.write("")
            st.info("**Triple-negative breast cancer** has no HER2, ER or PR receptor to target, so "
                    "receptor-targeted therapies do not apply. Treatment is usually chemotherapy or immunotherapy.")
    st.stop()

rec = receptors[receptors["receptor"] == p["receptor"]].iloc[0]
rec_drugs = drugs[drugs["receptor"] == p["receptor"]].sort_values("fda_year")
ranked = score(strategies[strategies["strategy_id"].isin(p["first"] + p["next"])])
ranked["Line"] = ranked["strategy_id"].apply(lambda s: "First line" if s in p["first"] else "After progression")
best = ranked[ranked["Line"] == "First line"].iloc[0]
nxt = ranked[ranked["Line"] == "After progression"]
res_rows = resistance[resistance["drug"].isin(p["resist_drugs"])]
rec_name = rec["receptor"] if rec["gene"] == rec["receptor"] else f"{rec['receptor']} ({rec['gene']})"
pct = {"HER2": 11.3, "ER": 70.9, "EGFR": 12.4}[p["receptor"]]

# ================= 1. RECEPTOR =================
with t1:
    st.write("")
    section(f"The receptor · {rec_name}", choice)
    c = st.columns(4)
    stat(c[0], rec_name, "Target receptor", "n")
    stat(c[1], rec["cell_location"], "Location in the cell")
    stat(c[2], f"{int(rec['length_aa']):,} aa", "Protein length", "g")
    stat(c[3], rec["cytoband"], f"Chromosome location", "n")
    st.write("")
    a, b = st.columns([1.3, 1])
    a.markdown(f'<div class="box"><h4>{rec["protein_name"]}</h4>'
               f'<p><span class="badge b-teal">{rec["receptor_type"]}</span></p><br>'
               f'<p><b>Role:</b> {rec["function"]}</p><br>'
               f'<p><b>How it is tested:</b> {rec["biomarker_test"]}</p><br>'
               f'<p><b>How common:</b> {p["prevalence"]}</p></div>', unsafe_allow_html=True)
    f = px.pie(names=[f"{rec['receptor']}-positive", "Other patients"], values=[pct, 100 - pct], hole=0.62,
               color_discrete_sequence=[TEAL, "#dfe7e5"], title="Patients with this receptor (TCGA)")
    f.update_traces(textinfo="none", sort=False)
    f.add_annotation(text=f"<b>{pct}%</b>", showarrow=False, font=dict(size=26, color=NAVY))
    b.plotly_chart(nice(f, 300), width="stretch")
    st.write("")
    section("Receptor structure · where the drugs act",
            f"Domain map of {rec['receptor']} ({int(rec['length_aa'])} amino acids) from UniProt {rec['uniprot_id']}")
    st.plotly_chart(domain_map(p["receptor"]), width="stretch")
    if p["receptor"] == "ER":
        st.caption("Aromatase inhibitors (letrozole, anastrozole) do not bind ER — they stop the body making oestrogen.")
    pdb = {"HER2": ("1N8Z", "HER2 bound to trastuzumab"), "EGFR": ("4ZAU", "EGFR kinase with osimertinib"),
           "ER": ("3ERT", "ER bound to tamoxifen (4-OHT)")}[p["receptor"]]
    html(f'<div class="box"><h4>See the 3D structure</h4><p>{pdb[1]} — '
         f'<a href="https://www.rcsb.org/structure/{pdb[0]}" target="_blank">PDB {pdb[0]}</a> · '
         f'<a href="https://alphafold.ebi.ac.uk/entry/{rec["uniprot_id"]}" target="_blank">AlphaFold model</a></p></div>')
    st.caption(f"Sources: NCBI Gene {rec['ncbi_gene_id']} · UniProt {rec['uniprot_id']} · cBioPortal (TCGA)")

# ================= 2. DRUGS =================
with t2:
    st.write("")
    section(f"Drugs that target {rec['receptor']}", f"{len(rec_drugs)} approved drugs · oldest to newest")
    a, b = st.columns([1, 1.4])
    f = px.pie(rec_drugs, names="drug_class", hole=0.55, color_discrete_sequence=PALETTE, title="Types of drug")
    f.update_traces(textinfo="value")
    a.plotly_chart(nice(f, 320), width="stretch")
    tl = rec_drugs.assign(short=rec_drugs["drug"].str.extract(r"\((.*)\)")[0].fillna(rec_drugs["drug"]))
    tl["pos"] = tl.groupby("drug_class").cumcount().map(lambda i: "top center" if i % 2 == 0 else "bottom center")
    f = px.scatter(tl, x="fda_year", y="drug_class", text="short", color="drug_class",
                   color_discrete_sequence=PALETTE, title="Approval timeline (FDA)",
                   labels={"fda_year": "Year approved", "drug_class": ""})
    f.update_traces(marker=dict(size=16, line=dict(width=2, color="white")), showlegend=False)
    f.for_each_trace(lambda t: t.update(textposition=list(tl.loc[tl.drug_class == t.name, "pos"])))
    f.update_xaxes(gridcolor="#e8eeec", range=[rec_drugs.fda_year.min() - 3, rec_drugs.fda_year.max() + 3])
    f.update_yaxes(range=[-0.6, tl.drug_class.nunique() - 0.4])
    b.plotly_chart(nice(f, 320), width="stretch")
    for row in [rec_drugs.iloc[i:i + 3] for i in range(0, len(rec_drugs), 3)]:
        cols = st.columns(3)
        for col, d in zip(cols, row.itertuples()):
            col.markdown(f'<div class="box"><h4>{d.drug} <span style="color:#8a99a8;font-weight:400;'
                         f'font-size:.85rem">({d.brand})</span></h4>'
                         f'<p><span class="badge b-teal">{d.drug_class}</span>'
                         f'<span class="badge b-navy">{d.route}</span>'
                         f'<span class="badge b-sage">FDA {d.fda_year}</span></p><br>'
                         f'<p>{d.mechanism}</p></div>', unsafe_allow_html=True)
    st.caption("Sources: ChEMBL, Drugs@FDA")

# ================= 3. BEST STRATEGY =================
with t3:
    st.write("")
    section("Which strategy works best?", choice)
    agree = " · agrees with NCCN/ESMO guidelines ✓" if best["strategy_id"] == p["guide_first"] else ""
    extra = ""
    if not nxt.empty:
        n = nxt.iloc[0]
        ok = " · agrees with guidelines ✓" if n["strategy_id"] == p["guide_next"] else ""
        extra = (f'<div style="margin-top:10px">If the cancer progresses: <b>{n["strategy"]}</b> '
                 f'({n["Score"]}/100){ok}</div>')
    html(f'<div class="win"><div style="color:#2c7a7b;font-weight:600;font-size:.85rem">RECOMMENDED FIRST'
         f'</div><div class="big">{best["strategy"]} · {best["Score"]}/100</div>'
         f'<div style="color:#4a5a6a">{agree.strip(" · ")}</div>{extra}</div>')
    fig = px.bar(ranked.iloc[::-1], x="Score", y="strategy", color="Line", orientation="h", text="Score",
                 color_discrete_map={"First line": TEAL, "After progression": "#9cc5b0"},
                 labels={"strategy": "", "Score": ""})
    fig.update_traces(marker_line_width=0, textposition="outside", width=0.6)
    fig.update_layout(height=120 + 48 * len(ranked), margin=dict(t=10, b=10, l=10),
                      legend_title_text="", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#4a5a6a"), legend=dict(orientation="h", y=1.08),
                      xaxis=dict(gridcolor="#e8eeec", range=[0, 105]))
    a, b = st.columns([1.25, 1])
    fig.update_layout(title="Overall score")
    a.plotly_chart(nice(fig, 120 + 60 * len(ranked)), width="stretch")
    crit = ["efficacy", "durability", "safety", "cost", "convenience"]
    names = ["Response", "Progression-free", "Safety", "Cost", "Convenience"]
    rad = go.Figure()
    for i, r in enumerate(ranked.itertuples()):
        vals = [getattr(r, c) for c in crit]
        rad.add_trace(go.Scatterpolar(r=vals + vals[:1], theta=names + names[:1], fill="toself", opacity=0.55,
                                      name=r.strategy.split(" (")[0], line_color=PALETTE[i % len(PALETTE)]))
    rad.update_layout(polar=dict(radialaxis=dict(range=[0, 5], showticklabels=False), bgcolor="rgba(0,0,0,0)"),
                      title="Strengths of each strategy (1–5)")
    b.plotly_chart(nice(rad, max(340, 120 + 60 * len(ranked))), width="stretch")
    st.dataframe(ranked[["strategy", "Line", "orr_pct", "pfs_months", "grade3_ae_pct", "Score", "Missing",
                         "trial"]].rename(
        columns={"strategy": "Strategy", "orr_pct": "Tumour response (%)",
                 "pfs_months": "Months without progression", "grade3_ae_pct": "Serious side effects (%)",
                 "trial": "Clinical trial", "Missing": "Not reported in trial"}),
        hide_index=True, width="stretch")
    # robustness check: does the winner stay the same with other sensible weights?
    alt = {"Clinical results only (no cost/convenience)": {"efficacy": 1, "durability": 1, "safety": 1,
                                                          "cost": 0, "convenience": 0},
           "More weight on effectiveness": {"efficacy": 4, "durability": 4, "safety": 2, "cost": 1, "convenience": 1},
           "More weight on safety": {"efficacy": 3, "durability": 3, "safety": 4, "cost": 1, "convenience": 1}}
    rows = []
    for label, w in alt.items():
        for line in ranked["Line"].unique():
            ids = p["first"] if line == "First line" else p["next"]
            top = score(strategies[strategies["strategy_id"].isin(ids)], w).iloc[0]
            orig = ranked[ranked["Line"] == line].iloc[0]
            rows.append(f'<p>• {label} ({line.lower()}): <b>{top["strategy"]}</b> '
                        + ('<span class="badge b-sage">same ✓</span>' if top["strategy_id"] == orig["strategy_id"]
                           else '<span class="badge b-grey">changes</span>') + '</p>')
    html('<div class="box"><h4>Robustness check · is the result stable?</h4>'
         '<p>The ranking was re-run with different weights to see if the best strategy changes.</p><br>'
         + "".join(rows) + '</div>')
    html('<div class="box"><h4>How the score works</h4><p>Each strategy gets 1–5 points for tumour response, '
         'months without progression, safety, cost and convenience, from phase 3 trials (PubMed). '
         'Weights: response 3 · progression-free time 3 · safety 2 · cost 1 · convenience 1. '
         'The total is shown out of 100. If a trial did not report a number, that criterion is left out and '
         'the other weights are re-scaled — nothing is guessed.<br><br><b>Note:</b> strategies come from '
         'different trials, so this is an <b>indirect comparison</b>, not a head-to-head test. Where possible a '
         'shared trial is used (e.g. osimertinib vs gefitinib/erlotinib in FLAURA).</p></div>')

# ================= 4. RESISTANCE =================
with t4:
    st.write("")
    section("If the drug stops working", choice)
    c = st.columns(3)
    stat(c[0], len(res_rows), "Resistance mechanisms", "n")
    stat(c[1], int((res_rows["evidence_level"] == "Clinical").sum()), "Clinical evidence")
    stat(c[2], int((res_rows["evidence_level"] != "Clinical").sum()), "Preclinical evidence", "g")
    st.write("")
    lab = list(res_rows["drug"].unique()) + list(res_rows["resistance_mechanism"].unique()) + \
        list(res_rows["rescue_strategy"].unique())
    idx = {l: i for i, l in enumerate(dict.fromkeys(lab))}
    labels = list(idx)
    col = [NAVY if l in set(res_rows["drug"]) else ("#c0563b" if l in set(res_rows["resistance_mechanism"])
                                                    else SAGE) for l in labels]
    src = [idx[d] for d in res_rows["drug"]] + [idx[m] for m in res_rows["resistance_mechanism"]]
    tgt = [idx[m] for m in res_rows["resistance_mechanism"]] + [idx[r] for r in res_rows["rescue_strategy"]]
    sk = go.Figure(go.Sankey(node=dict(label=labels, color=col, pad=14, thickness=16),
                             link=dict(source=src, target=tgt, value=[1] * len(src), color="rgba(44,122,123,.18)")))
    sk.update_layout(title="Drug  →  why it stops working  →  what to try next")
    st.plotly_chart(nice(sk, 120 + 42 * len(res_rows)), width="stretch")
    for drug_name, grp in res_rows.groupby("drug", sort=False):
        html(f'<div class="sec" style="font-size:1.05rem">{drug_name}</div>')
        for row in [grp.iloc[i:i + 2] for i in range(0, len(grp), 2)]:
            cols = st.columns(2)
            for col, r in zip(cols, row.itertuples()):
                ev = "b-sage" if r.evidence_level == "Clinical" else "b-grey"
                col.markdown(f'<div class="box"><p><span class="badge {ev}">{r.evidence_level}</span></p><br>'
                             f'<div class="flow"><span><b>Why it fails:</b> {r.resistance_mechanism}</span></div>'
                             f'<div class="flow" style="margin-top:6px"><span class="a">→ Try next:</span>'
                             f'<span>{r.rescue_strategy}</span></div></div>', unsafe_allow_html=True)
    st.caption("Sources: CIViC, PubMed")
