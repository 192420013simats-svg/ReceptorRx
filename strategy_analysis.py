import pandas as pd
import plotly.express as px
import streamlit as st

CRITERIA = ["efficacy", "safety", "durability", "cost", "convenience"]
RECEPTOR_CANCER = {"HER2": "Breast cancer", "ER": "Breast cancer", "EGFR": "Lung cancer"}
PROFILE_FIELDS = {
    "Breast cancer": {"her2_status": ("HER2 status", ["Positive", "Low", "Negative", "Not tested"]),
                      "er_status": ("ER status", ["Negative", "Positive", "Not tested"]),
                      "esr1_mutation": ("ESR1 mutation", ["Not tested", "Yes", "No"])},
    "Lung cancer": {"egfr_mutation": ("EGFR mutation", ["Ex19del", "L858R", "T790M", "None found", "Not tested"])},
}
LINES = {"First line (metastatic)": "First", "Second line or later": "Second"}
PRESETS = {
    "Clinical outcome focus": {"efficacy": 10, "safety": 5, "durability": 8, "cost": 2, "convenience": 2},
    "Patient experience focus": {"efficacy": 7, "safety": 10, "durability": 5, "cost": 4, "convenience": 9},
    "Low-resource setting": {"efficacy": 6, "safety": 6, "durability": 4, "cost": 10, "convenience": 8},
}
COST_SCORE = {"Generic oral": 5, "Generic injection": 4, "Branded oral": 3,
              "Branded oral + biologic": 2, "Branded biologic": 2, "ADC or bispecific": 1}
ROUTE_SCORE = {"Oral daily": 5, "Oral daily + oral chemo": 4, "IM injection monthly": 3,
               "IV every 3 weeks": 3, "IV every 3 weeks + oral": 2,
               "IV every 3 weeks + chemo": 2, "IV every 2 weeks + oral": 1}


@st.cache_data
def load():
    return (pd.read_csv("data/strategy_scores.csv"), pd.read_csv("data/eligibility_rules.csv"),
            pd.read_csv("data/guidelines.csv").sort_values("priority"))


def matches(profile, field, allowed):
    return profile.get(field, "Not tested") in str(allowed).split("|")


def eligible(scores, rules, profile, cancer, line):
    keep = []
    for _, r in rules.iterrows():
        receptor = scores.loc[scores["strategy_id"] == r["strategy_id"], "receptor"].iloc[0]
        if RECEPTOR_CANCER.get(receptor) == cancer and matches(profile, r["condition_field"], r["allowed_values"]) \
                and line in str(r["line_of_therapy"]).split("|"):
            keep.append(r["strategy_id"])
    return scores[scores["strategy_id"].isin(keep)].copy()


def trial_scores(df):
    """Convert published trial numbers into 1-5 scores. Missing number -> curated estimate."""
    out = df.copy()
    out["efficacy"] = df["orr_pct"].apply(lambda x: 1 + 4 * x / 100).fillna(df["efficacy"])
    out["durability"] = df["pfs_months"].apply(lambda x: 1 + 4 * min(x, 30) / 30).fillna(df["durability"])
    out["safety"] = df["grade3_ae_pct"].apply(lambda x: 5 - 4 * x / 100).fillna(df["safety"])
    out["cost"] = df["cost_tier"].map(COST_SCORE).fillna(df["cost"])
    out["convenience"] = df["route"].map(ROUTE_SCORE).fillna(df["convenience"])
    out["estimated"] = df.apply(lambda r: ", ".join(c for c, col in (("efficacy", "orr_pct"),
                                ("durability", "pfs_months"), ("safety", "grade3_ae_pct"))
                                if pd.isna(r[col])) or "none", axis=1)
    for c in CRITERIA:
        out[c] = out[c].round(2)
    return out


def rank(df, w):
    out = df.copy()
    total = sum(w.values())
    out["score"] = (sum(w[c] * out[c] for c in CRITERIA) / (5 * total) * 100).round(1)
    return out.sort_values("score", ascending=False).reset_index(drop=True)


def show_strategy():
    st.title("Strategy Evaluation")
    st.caption("Ranks receptor-targeted treatment strategies using published phase 3 trial results and your priorities")
    scores, rules, guidelines = load()

    # ================= USER INPUT =================
    with st.container(border=True):
        st.markdown("#### Input")
        a, b, c = st.columns(3)
        with a:
            st.markdown("**① Cancer and line of therapy**")
            cancer = st.selectbox("Cancer type", list(PROFILE_FIELDS.keys()))
            line_label = st.radio("Line of therapy", list(LINES.keys()))
        with b:
            st.markdown("**② Tumour profile**")
            profile = {}
            for field, (label, opts) in PROFILE_FIELDS[cancer].items():
                profile[field] = st.selectbox(label, opts, key=f"{cancer}_{field}")
        with c:
            st.markdown("**③ Your priorities** (0 = ignore, 10 = most important)")
            w = {"efficacy": st.slider("Efficacy (response rate)", 0, 10, 9),
                 "safety": st.slider("Safety (serious side effects)", 0, 10, 6),
                 "durability": st.slider("Durability (progression-free survival)", 0, 10, 7),
                 "cost": st.slider("Cost and access", 0, 10, 4),
                 "convenience": st.slider("Convenience (oral vs IV)", 0, 10, 3)}
        go_btn = st.button("Analyse", type="primary", key="analyse_strategy")

    if go_btn:
        if sum(w.values()) == 0:
            st.error("Set at least one priority above 0.")
            return
        line = LINES[line_label]
        el = trial_scores(eligible(scores, rules, profile, cancer, line))
        st.session_state["strategy_result"] = {"cancer": cancer, "line": line, "line_label": line_label,
                                               "profile": profile, "w": w, "el": el}

    if "strategy_result" not in st.session_state:
        st.info("Choose the input above and click **Analyse** to see the ranking.")
        return

    # ================= RESULTS =================
    out = st.session_state["strategy_result"]
    el, w = out["el"], out["w"]
    prof = ", ".join(f"{PROFILE_FIELDS[out['cancer']][k][0]}: {v}" for k, v in out["profile"].items())
    st.markdown(f"### Results: {out['cancer']} · {out['line_label']}")
    st.caption(f"Tumour profile: {prof}")
    if el.empty:
        st.warning("No strategy in the dataset matches this profile and line of therapy. "
                   "Try HER2 Positive, ER Positive, or an EGFR mutation.")
        return

    ranked = rank(el, w)
    best = ranked.iloc[0]
    tops = {name: rank(el, pw).iloc[0]["strategy"] for name, pw in PRESETS.items()}
    held = sum(t == best["strategy"] for t in tops.values())
    guide = None
    for _, g in guidelines.iterrows():
        if matches(out["profile"], g["condition_field"], g["allowed_values"]) and \
                out["line"] in str(g["line_of_therapy"]).split("|") and g["preferred_strategy_id"] in set(el["strategy_id"]):
            guide = g
            break

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Strategies compared", len(ranked))
    k2.metric("Top-ranked", best["strategy"].split(" (")[0], f"{best['score']}/100")
    k3.metric("Robustness", f"{held} of {len(tops)}", "scenarios keep the same top")
    if guide is not None:
        agree = guide["preferred_strategy_id"] == best["strategy_id"]
        k4.metric("Guideline agreement", "Agrees ✓" if agree else "Differs")

    left, right = st.columns([1.5, 1])
    with left, st.container(border=True):
        st.markdown("**Ranked strategies (score out of 100)**")
        fig = px.bar(ranked.iloc[::-1], x="score", y="strategy", orientation="h", text="score",
                     color="drug_type", labels={"score": "Weighted score", "strategy": "", "drug_type": "Drug type"})
        fig.update_traces(textposition="outside")
        fig.update_layout(height=120 + 60 * len(ranked), xaxis_range=[0, 105], margin=dict(t=10, b=10))
        st.plotly_chart(fig, width="stretch")
    with right, st.container(border=True):
        st.markdown("**Does the ranking hold if priorities change?**")
        for name, t in tops.items():
            st.write(f"{'✅' if t == best['strategy'] else '🔄'} {name}: **{t}**")
        st.markdown("**Does it agree with clinical guidelines?**")
        if guide is None:
            st.write("No guideline-preferred option among these strategies.")
        else:
            pref = ranked[ranked["strategy_id"] == guide["preferred_strategy_id"]]
            pos = int(pref.index[0]) + 1
            if pos == 1:
                st.success(f"Yes. Guidelines prefer **{pref.iloc[0]['strategy']}**, ranked #1 here.")
            else:
                st.warning(f"Guidelines prefer **{pref.iloc[0]['strategy']}**; it is ranked #{pos} with your priorities.")
            st.caption(f"Source: {guide['source']}")

    st.markdown("**Evidence behind each score**")
    table = ranked[["strategy", "drug_type", "orr_pct", "pfs_months", "grade3_ae_pct", "route", "cost_tier",
                    *CRITERIA, "score", "estimated", "trial"]].rename(columns={
        "orr_pct": "Response rate (%)", "pfs_months": "PFS (months)", "grade3_ae_pct": "Grade ≥3 side effects (%)",
        "estimated": "Estimated criteria"})
    st.dataframe(table, hide_index=True, width="stretch")
    st.latex(r"\text{Score} = \frac{\sum w_i\, s_i}{5\sum w_i}\times 100")
    st.caption("s (1–5): efficacy = 1 + 4 × response rate; durability = 1 + 4 × PFS/30; "
               "safety = 5 − 4 × grade ≥3 side-effect rate; cost and convenience from drug category and route. "
               "w = your priority. Trials enrolled different patients, so cross-trial comparison is approximate.")
    st.download_button("Download ranking (CSV)", table.to_csv(index=False),
                       file_name="strategy_ranking.csv", mime="text/csv")
