import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path

st.set_page_config(page_title="CEW Roster", page_icon="🔥", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800&family=Inter:wght@400;600;700&display=swap');
.stApp { background: #0b0c0f; color: #f5f5f5; font-family: Inter, sans-serif; }
.block-container { max-width: 1600px; padding-top: 2rem; }
h1, h2, h3 { font-family: 'Barlow Condensed', sans-serif !important; text-transform: uppercase; letter-spacing: 1px; color: #fff !important; }
div[data-testid="stImage"] img { border-radius: 8px; border-bottom: 3px solid #f04444; margin-bottom: 5px; }
.card-name { text-align: center; font-family: 'Barlow Condensed'; font-size: 1.3rem; font-weight: 700; color: #fff; line-height: 1.1; margin-top: 5px; }
.card-sub { text-align: center; font-size: 0.75rem; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.5px; }
.dual-tag { text-align: center; font-size: 0.65rem; color: #f04444; font-weight: 800; letter-spacing: 1px; margin-bottom: 15px; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# --- LOAD DATABASE ---
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "incinerator.db"

@st.cache_data(show_spinner="Loading Roster...")
def load_data():
    if not DB_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM wrestlers", conn)

df = load_data()
st.markdown("<h1 style='text-align:center; font-size: 3.5rem;'>🔥 CEW ROSTER</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align:center; color:#9ca3af !important; margin-bottom: 40px;'>CONTINENTAL ELITE WRESTLING</h3>", unsafe_allow_html=True)

if df.empty:
    st.error("Database not found or empty.")
else:
    # Function to display a 5-column grid
    def display_grid(dataframe):
        dataframe = dataframe.sort_values("canonical_name")
        rows = len(dataframe)
        for i in range(0, rows, 5):
            cols = st.columns(5)
            for j in range(5):
                if i + j < rows:
                    row = dataframe.iloc[i + j]
                    name = str(row.get("canonical_name", "Unknown"))
                    img_url = str(row.get("image_url", ""))
                    contract = str(row.get("contract_type", ""))
                    
                    with cols[j]:
                        # Image logic
                        if img_url and img_url != "nan" and img_url.strip():
                            st.image(img_url, use_container_width=True)
                        else:
                            st.markdown(f'<div style="background:#1f2229; height:250px; border-radius:8px; border-bottom:3px solid #f04444; display:flex; align-items:center; justify-content:center; font-size:2rem; color:#4a4f5c;">🔥</div>', unsafe_allow_html=True)
                        
                        # Name
                        st.markdown(f'<div class="card-name">{name}</div>', unsafe_allow_html=True)
                        
                        # Dual Contract Tag
                        if "DUAL" in contract.upper():
                            # Extracts the promotion name (e.g. "WWE/AAA" from "DUAL WITH WWE/AAA")
                            promo = contract.upper().replace("DUAL WITH", "").replace("DUAL", "").strip()
                            st.markdown(f'<div class="dual-tag">DUAL: {promo}</div>', unsafe_allow_html=True)
                        else:
                            st.markdown('<div class="dual-tag" style="opacity:0;">.</div>', unsafe_allow_html=True)


    # --- TABS ---
    tab_signed, tab_alumni = st.tabs(["📋 SIGNED ROSTER", "🎓 ALUMNI"])

    # --- TAB 1: SIGNED ROSTER ---
    with tab_signed:
        # Filter for SIGNED only
        signed_df = df[df["status"] == "SIGNED"]
        
        if signed_df.empty:
            st.warning("No signed wrestlers found. Check the database.")
        else:
            # MEN'S DIVISION
            st.markdown("### 👨 MEN'S DIVISION")
            men_df = signed_df[signed_df["gender"] == "MEN"]
            if not men_df.empty:
                display_grid(men_df)
            else:
                st.info("No men currently signed.")

            st.divider()

            # WOMEN'S DIVISION
            st.markdown("### 👩 WOMEN'S DIVISION")
            women_df = signed_df[signed_df["gender"] == "WOMEN"]
            if not women_df.empty:
                display_grid(women_df)
            else:
                st.info("No women currently signed.")

    # --- TAB 2: ALUMNI ---
    with tab_alumni:
        # Filter for ALUMNI only
        alumni_df = df[df["status"] == "ALUMNI"]
        
        if alumni_df.empty:
            st.info("No Alumni found.")
        else:
            display_grid(alumni_df)

    st.divider()

    # --- STAFF ---
    st.markdown("### 🎙️ CEW STAFF")
    staff_cols = st.columns(5)
    staff = ["Amit Kandari (President)", "Mauro Ranallo", "Don Callis", "Kevin Kelly"]
    for i, person in enumerate(staff):
        with staff_cols[i]:
            st.markdown(f'<div style="background:#1f2229; height:250px; border-radius:8px; border-bottom:3px solid #f04444; display:flex; align-items:center; justify-content:center; font-size:1.5rem; text-align:center; color:#fff; font-family:Barlow Condensed; font-weight:700; padding:10px;">{person}</div>', unsafe_allow_html=True)
