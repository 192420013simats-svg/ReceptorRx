import pandas as pd
import plotly.express as px
import requests
import streamlit as st

CBIO = "https://www.cbioportal.org/api"
ENTREZ = {"ERBB2": 2064, "ESR1": 2099, "EGFR": 1956}
ALTERATION_OPTIONS = ["Recommended for each receptor", "Amplification", "Mutation", "Amplification or mutation"]


@st.cache_data
def load_receptors():
    return pd.read_csv("data/receptors.csv")


@st.cache_data(show_spinner="Fetching patient data from cBioPortal…")
def tcga_alteration(gene, study, alteration):
    """Count TCGA patients with the receptor altered (live from cBioPortal)."""
    samples = set(requests.get(f"{CBIO}/sample-lists/{study}_all", timeout=30).json()["sampleIds"])
    body = {"sampleListId": f"{study}_all", "entrezGeneIds": [ENTREZ[gene]]}
    altered = set()
    if "Amplification" in alteration:
        url = f"{CBIO}/molecular-profiles/{study}_gistic/discrete-copy-number/fetch"
        rows = requests.post(url, json=body, params={"discreteCopyNumberEventType": "AMP"}, timeout=60).json()
        altered |= {r["sampleId"] for r in rows}
    if "utation" in alteration:
        url = f"{CBIO}/molecular-profiles/{study}_mutations/mutations/fetch"
        rows = requests.post(url, json=body, timeout=60).json()
        altered |= {r["sampleId"] for r in rows}
    return len(altered & samples), len(samples)


def show_receptors():
    st.title("Cancer Receptor Identification")
    st.caption("Sources: NCBI Gene, UniProt, cBioPortal (TCGA PanCancer Atlas)")
    df = load_receptors()

    # ================= USER INPUT =================
    with st.container(border=True):
        st.markdown("#### Input")
        c1, c2, c3 = st.columns(3)
        cancer = c1.selectbox("Cancer type", sorted(df["cancer"].unique()))
        options = list(df.loc[df["cancer"] == cancer, "receptor"])
        receptors = c2.multiselect("Receptors to analyse", options, default=options, key=f"rec_{cancer}")
        alteration = c3.selectbox("Alteration to count in patients", ALTERATION_OPTIONS,
                                  help="Recommended: HER2 = amplification, ER and EGFR = mutation")
        go_btn = st.button("Analyse", type="primary", key="analyse_receptors")

    if go_btn:
        if not receptors:
            st.error("Choose at least one receptor.")
            return
        rec = df[(df["cancer"] == cancer) & (df["receptor"].isin(receptors))]
        results = []
        for _, r in rec.iterrows():
            alt = r["alteration_counted"] if alteration == ALTERATION_OPTIONS[0] else alteration
            try:
                altered, total = tcga_alteration(r["gene"], r["tcga_study"], alt)
                results.append({"Receptor": r["receptor"], "Gene": r["gene"], "Alteration": alt,
                                "Altered patients": altered, "Total patients": total,
                                "% altered": round(100 * altered / total, 1)})
            except Exception as e:
                st.warning(f"Could not fetch patient data for {r['gene']}: {e}")
        st.session_state["receptor_result"] = {"cancer": cancer, "rec": rec, "res": pd.DataFrame(results)}

    if "receptor_result" not in st.session_state:
        st.info("Choose the input above and click **Analyse** to see the results.")
        return

    # ================= RESULTS =================
    out = st.session_state["receptor_result"]
    rec, res = out["rec"], out["res"]
    st.markdown(f"### Results: {out['cancer']}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Receptors identified", len(rec))
    c2.metric("Biomarker tests", rec["biomarker_test"].nunique())
    if not res.empty:
        c3.metric("TCGA patients analysed", f"{res['Total patients'].max():,}")

    cols = st.columns(len(rec))
    for col, (_, r) in zip(cols, rec.iterrows()):
        with col, st.container(border=True):
            st.markdown(f"### {r['receptor']} ({r['gene']})")
            st.caption(r["receptor_type"])
            st.write(f"**Protein:** {r['protein_name']} ({r['length_aa']} amino acids)")
            st.write(f"**Location in cell:** {r['cell_location']}")
            st.write(f"**Chromosome location:** {r['cytoband']} (gene size {r['gene_size_bp']:,} bp)")
            st.write(f"**Function:** {r['function']}")
            st.write(f"**Biomarker test:** {r['biomarker_test']}")
            st.markdown(f"[NCBI Gene {r['ncbi_gene_id']}](https://www.ncbi.nlm.nih.gov/gene/{r['ncbi_gene_id']}) · "
                        f"[UniProt {r['uniprot_id']}](https://www.uniprot.org/uniprotkb/{r['uniprot_id']})")

    if not res.empty:
        st.subheader("Receptor alteration in patients (TCGA)")
        fig = px.bar(res, x="Receptor", y="% altered", text="% altered", color="Receptor",
                     hover_data=["Gene", "Alteration", "Altered patients", "Total patients"],
                     color_discrete_sequence=["#1565c0", "#26a69a", "#ef6c00"])
        fig.update_traces(texttemplate="%{text}%", textposition="outside")
        fig.update_layout(height=380, showlegend=False, yaxis_title="% of patients")
        st.plotly_chart(fig, width="stretch")
        st.dataframe(res, hide_index=True, width="stretch")
        st.caption("This is genomic alteration (amplification or mutation), not IHC protein positivity.")
        st.download_button("Download results (CSV)", res.to_csv(index=False),
                           file_name=f"receptors_{out['cancer']}.csv", mime="text/csv")
