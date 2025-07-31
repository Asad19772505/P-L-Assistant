import streamlit as st
import pandas as pd
import os

from src.export import export_excel
from src.narrative import generate_commentary

st.set_page_config(page_title="P&L Analysis Assistant", layout="wide")

@st.cache_data
def load_csv(file_like):
    df = pd.read_csv(file_like)
    df['period'] = pd.to_datetime(df['period'])
    return df

st.title("P&L Analysis Assistant")

st.markdown("""
**Steps**
1) Upload your P&L fact extract (CSV) and your Chart of Accounts mapping (CSV).
2) Select period and grouping to view standardized P&L with variances.
3) Review top variance drivers and generate commentary (GROQ).
4) Export to Excel.
""")

# --- Inputs ---
pnl_file = st.file_uploader("Upload P&L fact (CSV)", type=["csv"])
coa_file = st.file_uploader("Upload Chart of Accounts map (CSV)", type=["csv"])
fx_file  = st.file_uploader("Upload FX rates (CSV, optional)", type=["csv"])

# GROQ API Key
with st.expander("AI Commentary Settings (GROQ)"):
    default_key = os.getenv("GROQ_API_KEY", "")
    api_key = st.text_input("GROQ API Key", value=default_key, type="password", help="Set env var GROQ_API_KEY or paste here.")
    model_info = st.caption("Model: llama-3.1-70b-versatile (via groq)")

client = None
if api_key:
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
    except Exception as e:
        st.warning(f"GROQ client not available: {e}")

if pnl_file and coa_file:
    pnl = load_csv(pnl_file)
    coa = load_csv(coa_file)

    # join & validate mapping
    df = pnl.merge(coa[['account_code','category','subcategory','sign']], on="account_code", how="left")
    unmapped = df[df['category'].isna()]['account_code'].unique()
    if len(unmapped) > 0:
        st.warning(f"{len(unmapped)} unmapped account codes detected. Please update coa_map.csv.")
        with st.expander("Unmapped account_code list"):
            st.write(pd.DataFrame({'account_code': unmapped}))

    # numeric safety
    for col in ['actual','budget','prior_year']:
        if col not in df.columns:
            df[col] = 0.0

    # sign conventions
    df['actual_signed'] = df['actual'] * df['sign']
    df['budget_signed'] = df['budget'] * df['sign']
    df['prior_signed']  = df['prior_year'] * df['sign']

    # filters
    periods = sorted(df['period'].dt.to_period('M').unique())
    period = st.selectbox("Period", periods, index=len(periods)-1 if periods else 0)
    view = st.selectbox("View by", ["Total", "business_unit", "cost_center"])
    group_cols = []
    if view != "Total":
        group_cols = [view]
    dff = df[df['period'].dt.to_period('M') == period]

    # aggregate P&L
    piv = (dff
           .groupby(group_cols + ['category','subcategory'], dropna=False)
           .agg(actual=('actual_signed','sum'),
                budget=('budget_signed','sum'),
                prior=('prior_signed','sum'))
           .reset_index())
    piv['var_abs'] = piv['actual'] - piv['budget']
    piv['var_pct'] = (piv['var_abs'] / piv['budget'].abs()).replace([pd.NA, pd.NaT, float('inf'), -float('inf')], 0)

    st.subheader("Standard P&L (Actual vs Budget)")
    st.dataframe(piv, use_container_width=True)

    # top drivers
    drivers = (piv.assign(abs_driver=piv['var_abs'].abs())
                 .sort_values('abs_driver', ascending=False)
                 .head(10))
    st.subheader("Top Variance Drivers")
    st.dataframe(drivers[['category','subcategory','var_abs','var_pct']], use_container_width=True)

    # totals table for prompt context
    totals = (piv[['actual','budget','prior']].sum().to_frame().T)
    totals['var_abs'] = totals['actual'] - totals['budget']
    totals['var_pct'] = (totals['var_abs'] / totals['budget'].abs()).replace([pd.NA, pd.NaT, float('inf'), -float('inf')], 0)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Explain variances with GROQ", use_container_width=True):
            if client is None:
                st.error("Please provide a valid GROQ API key in the settings above.")
            else:
                # Build compact summary table for the prompt
                summary_cols = ['category','subcategory','var_abs','var_pct','actual','budget']
                summary = drivers[summary_cols].copy()
                try:
                    from src.narrative import generate_commentary
                    text = generate_commentary(summary, totals, str(period), view if view!="Total" else "Company")
                    st.success("Generated commentary:")
                    st.markdown(text)
                except Exception as e:
                    st.error(f"Failed to generate commentary: {e}")

    with col2:
        if st.button("Export Excel", use_container_width=True):
            try:
                meta = {
                    "period": str(period),
                    "view": view,
                    "generated_by": "P&L Analysis Assistant",
                }
                xls_bytes = export_excel(piv, drivers, meta)
                st.download_button(
                    "Download P&L Pack (Excel)",
                    data=xls_bytes,
                    file_name=f"pnl_pack_{str(period)}_{view}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Excel export failed: {e}")
else:
    st.info("Upload P&L and CoA mapping to begin.")
