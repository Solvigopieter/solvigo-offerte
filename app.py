# Home.py
import streamlit as st

st.set_page_config(page_title="Solvigo • Offertegenerator", layout="wide")
st.title("Solvigo Offertegenerator")

st.markdown("""
Gebruik de **sidebar** links om te wisselen tussen:
- **PV Offerte** (jouw bestaande tool)
- **Paraboolspiegels – handmatig**
""")

st.info("Tip: deze opzet laat de UI direct switchen zonder refactor van je bestaande PV-code.")
