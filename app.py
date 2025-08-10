import streamlit as st
import pandas as pd
from pathlib import Path

# --- BEGIN: path safety patch (added by fix_imports.py) ---
import sys as _sys, os as _os
# Ensure the project root is on sys.path for 'from src...' imports
_pr = _os.path.dirname(__file__)
if _pr not in _sys.path:
    _sys.path.append(_pr)
# --- END: path safety patch (added by fix_imports.py) ---

from src.export import export_excel

st.set_page_config(layout="centered")

st.title("Excel Exporter App")

st.write(
    "This is a simple app that demonstrates a common project structure where the main script (`app.py`) "
    "imports a function from a module inside a `src` directory."
)

st.info("Click the button below to generate and download a sample Excel file.")

# --- App Logic ---
# Create some sample data
data = {
    'Product': ['Apples', 'Oranges', 'Bananas', 'Grapes'],
    'Sales (USD)': [1200, 950, 1500, 750],
    'Region': ['North', 'South', 'North', 'East']
}
df = pd.DataFrame(data)

st.subheader("Sample Data to Export")
st.dataframe(df, use_container_width=True)

# --- Download Button ---
if st.button("Generate Excel File", type="primary"):
    try:
        # Call the imported function to get the Excel data in memory
        excel_data = export_excel(df)

        st.balloons()
        st.success("Excel file generated successfully!")

        # Provide a download button for the in-memory file
        st.download_button(
            label="📥 Download Excel File",
            data=excel_data,
            file_name="sample_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        st.error(f"An error occurred: {e}")

st.markdown("---")
st.write("Made with ❤️ for demonstrating Python imports.")
