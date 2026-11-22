import streamlit as st
from receptor_analysis import show_receptors
from drug_analysis import show_drugs
from strategy_analysis import show_strategy
from resistance_analysis import show_resistance

st.set_page_config(page_title="ReceptorRx", page_icon="🧬", layout="wide")

st.sidebar.title("🧬 ReceptorRx")
st.sidebar.caption("Receptor-targeted cancer therapy evaluation")
page = st.sidebar.radio("Navigation", [
    "Home",
    "Cancer Receptor Identification",
    "Receptor-Targeted Drug Analysis",
    "Strategy Evaluation",
    "Resistance → Rescue",
])

if page == "Home":
    st.title("🧬 ReceptorRx")
    st.subheader("Evaluation of Receptor-Targeted Therapeutic Strategies for Cancer Treatment")
    st.write("ReceptorRx identifies cancer receptors, analyses the drugs that target them, "
             "ranks treatment strategies and maps what to use when resistance develops.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cancers", "2", "Breast, Lung")
    c2.metric("Receptors", "3", "HER2, ER, EGFR")
    c3.metric("Data sources", "6", "NCBI, UniProt, …")
    c4.metric("Strategies ranked", "12")

    st.markdown("### How it works")
    st.markdown("1. **Cancer Receptor Identification:** choose a cancer and see its receptors\n"
                "2. **Receptor-Targeted Drug Analysis:** choose a receptor and see its drugs\n"
                "3. **Strategy Evaluation:** set your priorities and rank the treatments\n"
                "4. **Resistance → Rescue:** choose a drug and see what to use if it stops working")
    st.info("For education and research only. Not for clinical decisions.")

elif page == "Cancer Receptor Identification":
    show_receptors()

elif page == "Receptor-Targeted Drug Analysis":
    show_drugs()

elif page == "Strategy Evaluation":
    show_strategy()

elif page == "Resistance → Rescue":
    show_resistance()
