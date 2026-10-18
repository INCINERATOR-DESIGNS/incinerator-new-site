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
.champion-tag { text-align: center; font-size: 0.65rem; color: #f04444; font-weight: 800; letter-spacing: 1px; margin-bottom: 15px; }
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
        # Sort alphabetically by canonical_name
        dataframe = dataframe.sort_values("canonical_name")
        rows = len(dataframe)
        for i in range(0, rows, 5):
            cols = st.columns(5)
            for j in range(5):
                if i + j < rows:
                    row = dataframe.iloc[i + j]
                    name = str(row.get("canonical_name", "Unknown"))
                    img_url = str(row.get("image_url", ""))
                    
                    with cols[j]:
                        if img_url and img_url != "nan" and img_url.strip():
                            st.image(img_url, use_container_width=True)
                        else:
                            # Placeholder if no image
                            st.markdown(f'<div style="background:#1f2229; height:250px; border-radius:8px; border-bottom:3px solid #f04444; display:flex; align-items:center; justify-content:center; font-size:2rem; color:#4a4f5c;">🔥</div>', unsafe_allow_html=True)
                        
                        st.markdown(f'<div class="card-name">{name}</div>', unsafe_allow_html=True)
                        
                        # Check if champion (you can update these names as titles change)
                        champions = ["Josh Alexander", "Giulia", "Gabe Kidd", "Starlight Kid"]
                        if name in champions:
                            st.markdown('<div class="champion-tag">🏆 CHAMPION</div>', unsafe_allow_html=True)
                        else:
                            st.markdown('<div class="champion-tag" style="opacity:0;">.</div>', unsafe_allow_html=True)

    # 1. CHAMPIONS SECTION
    st.markdown("### 👑 THE CHAMPIONS")
    # List the exact names of your current champions here
    champ_names = ["Josh Alexander", "Giulia", "Gabe Kidd", "Starlight Kid", "Dezmond Xavier", "Zachary Wentz", "Myron Reed"]
    champs_df = df[df["canonical_name"].isin(champ_names)]
    if not champs_df.empty:
        display_grid(champs_df)
    else:
        st.info("Champions not found in database. Check names.")

    st.divider()

    # 2. MEN'S DIVISION
    st.markdown("### 👨 MEN'S DIVISION")
    # Assume women have 'W' or 'Women' in their division column, or we filter by specific names
    women_names = ["Giulia", "Starlight Kid", "Kairi", "Mariah May", "Dani Luna", "Killer Kelly", "Rina", "Miyu Yamashita", "Sol Ruca", "La Catalina", "Isla Dawn", "Kay Lee Ray", "Myla Grace", "Priscilla Kelly", "Kelani Jordan", "Kendal Grey", "Zaria", "Zayda Steel", "Angel Hayze", "Dani Luna", "Charlie", "Maddy Morgan", "Brook Havok"]
    
    men_df = df[~df["canonical_name"].isin(women_names)]
    display_grid(men_df)

    st.divider()

    # 3. WOMEN'S DIVISION
    st.markdown("### 👩 WOMEN'S DIVISION")
    women_df = df[df["canonical_name"].isin(women_names)]
    display_grid(women_df)

    st.divider()

    # 4. STAFF
    st.markdown("### 🎙️ CEW STAFF")
    staff_cols = st.columns(5)
    staff = ["Amit Kandari (President)", "Mauro Ranallo", "Don Callis", "Kevin Kelly"]
    for i, person in enumerate(staff):
        with staff_cols[i]:
            st.markdown(f'<div style="background:#1f2229; height:250px; border-radius:8px; border-bottom:3px solid #f04444; display:flex; align-items:center; justify-content:center; font-size:1.5rem; text-align:center; color:#fff; font-family:Barlow Condensed; font-weight:700; padding:10px;">{person}</div>', unsafe_allow_html=True)
