from pathlib import Path
import html
import os
import re
import shutil
import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent

# Website browsing uses the main database. INCINERATOR_DB_PATH can override it.
DATABASE = Path(
    os.environ.get("INCINERATOR_DB_PATH", str(BASE_DIR / "incinerator.db"))
).expanduser().resolve()

# Match imports use a separate working-copy database only.
WORKING_DB_CANDIDATES = [
    BASE_DIR / "incinerator_working.db",
    BASE_DIR / "incinerator_working_championships.db",
    BASE_DIR / "INCINERATOR_WORKING_COPY.db",
]
WORKING_DATABASE = next(
    (path.resolve() for path in WORKING_DB_CANDIDATES if path.is_file()),
    None,
)

LOGO_PATH = BASE_DIR / "incinerator.jpg"
IMPORT_ENABLED = os.environ.get("INCINERATOR_ENABLE_IMPORTER", "0") == "1"

st.set_page_config(page_title="INCINERATOR | CEW Database", page_icon="🔥", layout="wide", initial_sidebar_state="expanded")

st.markdown(r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800&family=Inter:wght@400;600;700&display=swap');
:root{--fire:#f04444;--ink:#0b0c0f;--panel:#15171c;--line:#2b2e36;--muted:#9ca3af}

.stApp{background:radial-gradient(ellipse at 15% -15%,#341719 0%,#111216 36%,#0b0c0f 78%);color:#f5f5f5;font-family:Inter,sans-serif}
.block-container{max-width:1440px;padding-top:2rem;padding-bottom:3rem}

section[data-testid="stSidebar"]{background:#101115;border-right:1px solid #292b31;min-width:320px !important;max-width:320px !important;}
section[data-testid="stSidebar"] [data-testid="stImage"] img{background:transparent !important;border-radius:0px;margin-bottom:12px;padding:0 5px}

h1,h2,h3{font-family:'Barlow Condensed',sans-serif!important;letter-spacing:.3px}
h1{font-size:3.3rem!important;font-weight:800!important;color:#fff!important} h2{font-size:2rem!important;color:#fff!important} h3{font-size:1.35rem!important;color:#fff!important}
.eyebrow{color:#ff6868;text-transform:uppercase;letter-spacing:2.5px;font-weight:800;font-size:.72rem}

.hero{border:1px solid #49282c;background:linear-gradient(115deg,rgba(103,24,31,.56),rgba(24,25,31,.92) 54%,rgba(19,20,25,.96));border-radius:18px;padding:26px 30px;margin:6px 0 22px;position:relative;overflow:hidden}
.hero-title{font-family:'Barlow Condensed';font-size:3.2rem;font-weight:800;line-height:1.05;color:white}.hero-sub{color:#c7c7cc;font-size:.92rem;margin-top:8px;letter-spacing:.6px}

.metric{background:linear-gradient(145deg,#1b1d23,#131419);border:1px solid #30323b;border-radius:13px;padding:17px 19px;min-height:105px}.metric-label{font-size:.76rem;color:#aeb2bc;text-transform:uppercase;letter-spacing:1.2px;font-weight:700}.metric-value{font-family:'Barlow Condensed';font-size:2.55rem;line-height:1.1;color:#fff;font-weight:700;margin-top:6px}.metric-value.red{color:#ff6262}

.match-card,.profile-card{background:linear-gradient(145deg,#191b21,#111216);border:1px solid #30323b;border-radius:15px;padding:17px 19px;margin:0 0 13px}.match-meta{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;color:#a6aab4;font-size:.75rem;font-weight:700;letter-spacing:.7px;text-transform:uppercase}.match-type{display:inline-block;background:#302024;border:1px solid #6c3038;color:#ff9696;border-radius:99px;padding:3px 9px;font-size:.69rem;font-weight:800}.matchup{font-family:'Barlow Condensed';font-size:1.42rem;font-weight:700;line-height:1.25;color:#f7f7f8;margin:13px 0 10px;overflow-wrap:anywhere}.match-bottom{border-top:1px solid #2c2e35;padding-top:11px;display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;color:#c4c7ce;font-size:.82rem}.winner{color:#86efac;font-weight:800}.rating{font-weight:800}.review{color:#ffbd69;font-size:.72rem;font-weight:700}.profile-name{font-family:'Barlow Condensed';font-size:1.35rem;font-weight:700;color:#fff}.profile-sub{color:#a6aab4;font-size:.77rem;margin-top:4px}
.stButton>button{border-radius:9px;border:1px solid #4a3034;background:#21171a;color:#fff;font-weight:700}.stButton>button:hover{border-color:#f04444;color:#fff;background:#351b20}hr{border-color:#2d3038}footer{visibility:hidden}

div[data-testid="stSidebarNav"] {display: none !important;}
div[data-testid="stRadio"] {display: none !important;}

.nav-container {display: flex; flex-direction: column; gap: 8px; margin-top: 15px;}
.stButton > button[key^="nav_"] {
    background: #16171d !important;
    border: 1px solid #252730 !important;
    color: #9ca3af !important;
    border-radius: 6px !important;
    padding: 12px 14px !important;
    text-align: left !important;
    font-size: 0.85rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.8px !important;
    width: 100% !important;
    transition: all 0.2s ease-in-out !important;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner="Connecting to the CEW archive…")
def load_tables(db_path: str):
    path = Path(db_path)
    if not path.exists(): return {}
    uri = path.as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        names = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name", conn)["name"].tolist()
        return {name: pd.read_sql_query(f'SELECT * FROM "{name.replace(chr(34), chr(34)*2)}"', conn) for name in names}

def table(tables, name): return tables.get(name, pd.DataFrame())
def clean(v, default=""):
    if v is None or pd.isna(v) or str(v).strip().lower() in {"", "none", "nan"}: return default
    return str(v).strip()
def esc(v): return html.escape(str(v))
def datefmt(v):
    v = clean(v)
    if not v: return "DATE NOT RECORDED"
    try: return pd.to_datetime(v).strftime("%d %b %Y").upper()
    except Exception: return v.upper()
def metric(label, value, red=False):
    st.markdown(f'<div class="metric"><div class="metric-label">{esc(label)}</div><div class="metric-value {"red" if red else ""}">{esc(value)}</div></div>', unsafe_allow_html=True)
def match_card(r):
    rating = clean(r.get("rating", ""))
    try:
        score = float(rating); rating_text = f"★ {score:g}"; color = "#f5c542" if score >= 4.75 else "#22c55e" if score >= 4 else "#3b82f6" if score >= 2.75 else "#ef4444"
    except (ValueError, TypeError): rating_text, color = "UNRATED", "#9ca3af"
    meta = f'#{esc(clean(r.get("match_number", r.get("id", "—"))))} · {esc(clean(r.get("event"), "EVENT NOT RECORDED"))} · {esc(datefmt(r.get("event_date")))}'
    details = [f'FINISH · {esc(clean(r.get("finish"), "NOT RECORDED"))}']
    if clean(r.get("match_time")): details.append(f'TIME · {esc(clean(r.get("match_time")))}')
    if clean(r.get("venue")): details.append(f'VENUE · {esc(clean(r.get("venue")))}')
    review = '<span class="review">⚠ NEEDS DATA REVIEW</span>' if clean(r.get("review_required"), "0") in {"1", "True", "true"} else ""
    st.markdown(f'<div class="match-card"><div class="match-meta"><span>{meta}</span><span class="match-type">{esc(clean(r.get("match_type"), "MATCH"))}</span></div><div class="matchup">{esc(clean(r.get("match_card"), "MATCHUP NEEDS REVIEW"))}</div><div class="match-bottom"><span>RESULT · <span class="winner">{esc(clean(r.get("result"), "RESULT NOT RECORDED"))}</span></span><span class="rating" style="color:{color}">{rating_text}</span><span>{" · ".join(details)}</span>{review}</div></div>', unsafe_allow_html=True)

try: tables = load_tables(str(DATABASE))
except Exception as e:
    st.error("The database could not be read."); st.exception(e); st.stop()
if not tables: st.error(f"No database tables found at {DATABASE}."); st.stop()
profiles, matches, history = table(tables,"wrestler_profiles"), table(tables,"matches"), table(tables,"wrestler_match_history")
teams, factions = table(tables,"teams"), table(tables,"factions")
team_members, faction_members = table(tables,"team_members"), table(tables,"faction_members")
wrestlers = table(tables,"wrestlers")
if not wrestlers.empty and "id" in wrestlers and "canonical_name" in wrestlers:
    wrestler_name_by_id = {str(r["id"]): clean(r["canonical_name"], "Unknown wrestler") for _, r in wrestlers.iterrows()}
else:
    wrestler_name_by_id = {}
def group_members(member_df, group_id, group_key):
    if member_df.empty or group_key not in member_df.columns or "wrestler_id" not in member_df.columns: return []
    rows = member_df[member_df[group_key].astype(str) == str(group_id)]
    out = []
    for _, member in rows.iterrows():
        name = wrestler_name_by_id.get(str(member.get("wrestler_id")), f"Wrestler ID {member.get('wrestler_id')}")
        status = clean(member.get("membership_status"), "CONFIRMED")
        role = clean(member.get("role"))
        suffix = f" — {role}" if role and role.lower() not in {"none", "nan"} else ""
        if status not in {"CONFIRMED", "ACTIVE"}: suffix += f" [{status}]"
        out.append(name + suffix)
    return out

if "navigation_page" not in st.session_state:
    st.session_state["navigation_page"] = "Dashboard"

with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), use_container_width=True)
    else:
        st.markdown('<div class="eyebrow">CEW DATABASE</div><div style="font-family:Barlow Condensed;font-size:2rem;font-weight:800;margin:2px 0 4px">🔥 INCINERATOR</div>', unsafe_allow_html=True)
    
    st.markdown('<div style="color:#656974;font-size:.72rem;letter-spacing:1px;font-weight:700;margin:14px 0 4px">THE WRESTLING RECORD</div>', unsafe_allow_html=True)
    
    pages = ["Dashboard", "Match Explorer", "Wrestler Directory", "Events & FUSION", "Championships", "Teams & Factions", "Data Review"]
    if IMPORT_ENABLED and WORKING_DATABASE is not None: pages.append("Match Importer")
    
    st.markdown('<div class="nav-container">', unsafe_allow_html=True)
    for p in pages:
        button_label = p.upper()
        if st.session_state["navigation_page"] == p:
            st.markdown(f'**{button_label}**', unsafe_allow_html=True)
        else:
            if st.button(button_label, key=f"nav_btn_{p}", use_container_width=True):
                st.session_state["navigation_page"] = p
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.divider()
    st.caption("LOCAL WORKING COPY" if IMPORT_ENABLED else "PUBLIC READ-ONLY EDITION")
    st.caption(f"Database: {DATABASE.name}")

page = st.session_state["navigation_page"]

st.markdown('<div class="hero"><div class="hero-title">CONTINENTAL ELITE WRESTLING</div><div class="hero-sub">INCINERATOR · WRESTLERS · MATCHES · FUSION · HISTORY · LEGACY</div></div>', unsafe_allow_html=True)

if page == "Dashboard":
    st.markdown("## THE ARCHIVE AT A GLANCE")
    a,b,c,d = st.columns(4)
    with a: metric("Wrestler profiles",len(profiles),True)
    with b: metric("Recorded matches",len(matches))
    with c: metric("Match history rows",len(history))
    with d: metric("Teams tracked",len(teams))
    st.markdown("## Latest results")
    if not matches.empty:
        latest = matches.copy()
        sortcols = [c for c in ["event_date","match_number"] if c in latest]
        if sortcols: latest = latest.sort_values(sortcols,ascending=[False]*len(sortcols),na_position="last")
        for _,r in latest.head(5).iterrows(): match_card(r)
    else: st.info("No match records are available yet.")
    st.markdown("## Find your next rabbit hole")
    x,y,z = st.columns(3)
    with x:
        st.markdown("**MATCH EXPLORER**\n\nSearch results by wrestler, event, finish or match type.")
        if st.button("Explore matches",use_container_width=True,key="dash_to_explorer"):
            st.session_state["navigation_page"] = "Match Explorer"
            st.rerun()
    with y:
        st.markdown("**WRESTLER DIRECTORY**\n\nBrowse career records and connected match history.")
        if st.button("Browse wrestlers",use_container_width=True,key="dash_to_directory"):
            st.session_state["navigation_page"] = "Wrestler Directory"
            st.rerun()
    with z:
        st.markdown("**DATA REVIEW**\n\nIdentify records flagged for a closer look.")
        if st.button("Review flagged data",use_container_width=True,key="dash_to_review"):
            st.session_state["navigation_page"] = "Data Review"
            st.rerun()

elif page == "Match Explorer":
    st.markdown("## Match Explorer")
    st.caption("Search match details AND linked participant names.")
    if matches.empty: st.info("No matches found.")
    else:
        df = matches.copy()
        f1, f2, f3 = st.columns(3)
        with f1: query = st.text_input("Search match / wrestler / event",placeholder="e.g. Giulia, FUSION EP 5, Dogs…")
        with f2:
            types = sorted(df.match_type.dropna().astype(str).unique()) if "match_type" in df else []
            chosen_type = st.selectbox("Match type",["All types"]+types)
        with f3:
            shows = sorted(df.side.dropna().astype(str).unique()) if "side" in df else []
            chosen_show = st.selectbox("Show",["All shows"]+shows)
        f4, f5 = st.columns(2)
        with f4:
            events = sorted(df.event.dropna().astype(str).unique()) if "event" in df else []
            chosen_event = st.selectbox("Event",["All events"]+events)
        with f5: flagged_only = st.checkbox("Only records flagged for review")
        if query.strip():
            query_terms = [t for t in re.findall(r"[a-z0-9]+", query.casefold()) if t not in {"vs", "v", "versus", "and", "the"}]
            participants = table(tables, "match_participants")
            wrestlers = table(tables, "wrestlers")
            aliases = table(tables, "name_aliases")
            linked_text = {}
            if not participants.empty and "match_id" in participants.columns:
                pm = participants.copy()
                if not wrestlers.empty and "wrestler_id" in pm and "id" in wrestlers and "canonical_name" in wrestlers:
                    name_map = wrestlers.set_index("id")["canonical_name"].to_dict()
                    pm["_linked_name"] = pm["wrestler_id"].map(name_map).fillna("")
                else:
                    pm["_linked_name"] = ""
                if not aliases.empty and {"wrestler_id", "alias"}.issubset(aliases.columns):
                    alias_map = aliases.groupby("wrestler_id")["alias"].apply(lambda x: " ".join(x.dropna().astype(str))).to_dict()
                    pm["_aliases"] = pm["wrestler_id"].map(alias_map).fillna("")
                else:
                    pm["_aliases"] = ""
                for mid, group in pm.groupby("match_id", dropna=False):
                    bits = []
                    for col in ["source_label", "team_name", "_linked_name", "_aliases", "result", "parse_note"]:
                        if col in group.columns:
                            bits.extend(group[col].dropna().astype(str).tolist())
                    linked_text[str(mid)] = " ".join(bits)
            searchable_cols = [c for c in ["match_card", "result", "finish", "event", "venue", "match_type", "commentary"] if c in df.columns]
            keep = []
            for _, match_row in df.iterrows():
                bits = [str(match_row.get(c, "") or "") for c in searchable_cols]
                bits.append(linked_text.get(str(match_row.get("id", "")), ""))
                text_blob = re.sub(r"[^a-z0-9]+", " ", " ".join(bits).casefold())
                keep.append(bool(query_terms) and all(term in text_blob for term in query_terms))
            df = df.loc[pd.Series(keep, index=df.index)]
        if chosen_type != "All types" and "match_type" in df: df = df[df.match_type.astype(str)==chosen_type]
        if chosen_show != "All shows" and "side" in df: df = df[df.side.astype(str)==chosen_show]
        if chosen_event != "All events" and "event" in df: df = df[df.event.astype(str)==chosen_event]
        if flagged_only and "review_required" in df: df = df[df.review_required.fillna(0).astype(str).isin(["1","True","true"])]
        sc=[c for c in ["event_date","match_number"] if c in df]
        if sc: df=df.sort_values(sc,ascending=[False]*len(sc),na_position="last")
        st.markdown(f'**{len(df)} MATCHES IN VIEW**',unsafe_allow_html=True)
        size=st.selectbox("Results per page", [20, 40, 80], index=1); n=max(1,(len(df)+size-1)//size)
        pg=st.number_input("Page",min_value=1,max_value=n,value=1,step=1)
        for _,r in df.iloc[(int(pg)-1)*size:int(pg)*size].iterrows(): match_card(r)
        if df.empty: st.info("No matches fit those filters. Try clearing one or more filters.")

elif page == "Wrestler Directory":
    st.markdown("## Wrestler Directory"); st.caption("Career records connected to the match-history archive.")
    if profiles.empty: st.info("No profiles found.")
    else:
        df=profiles.copy(); q=st.text_input("Search the roster",placeholder="Search a wrestler's name…")
        status=st.selectbox("Roster status",["Everyone","Active roster","Alumni / inactive"])
        if q: df=df[df.canonical_name.fillna("").astype(str).str.contains(q,case=False,regex=False)]
        if status!="Everyone" and "active" in df: df=df[df.active.fillna(0).astype(int)==(1 if status=="Active roster" else 0)]
        sort=st.selectbox("Sort by",["Name","Most matches","Most wins","Win percentage","Highest average rating"])
        col={"Name":"canonical_name","Most matches":"total_matches","Most wins":"wins","Win percentage":"win_percentage","Highest average rating":"average_match_rating"}[sort]
        if col in df: df=df.sort_values(col,ascending=(sort=="Name"),na_position="last")
        st.caption(f"{len(df)} wrestlers")
        for idx in range(0,len(df),2):
            cols=st.columns(2)
            for j in range(2):
                if idx+j>=len(df): continue
                r=df.iloc[idx+j]; name=clean(r.get("canonical_name"),"Unknown wrestler")
                with cols[j]:
                    st.markdown(f'<div class="profile-card"><div style="float:right" class="profile-sub">{"ACTIVE" if clean(r.get("active"),"0")=="1" else "ALUMNI / INACTIVE"}</div><div class="profile-name">{esc(name)}</div><div class="profile-sub">{esc(clean(r.get("teams"),"No team recorded"))} · {esc(clean(r.get("factions"),"No faction recorded"))}</div><div style="margin-top:10px;font-size:.85rem"><b>{esc(clean(r.get("wins"),"0"))}</b>–<b>{esc(clean(r.get("losses"),"0"))}</b>–<b>{esc(clean(r.get("draws"),"0"))}</b> W / L / D · <b>{esc(clean(r.get("total_matches"),"0"))}</b> matches</div><div style="color:#9ca3af;font-size:.78rem;margin-top:4px">Win percentage: {esc(clean(r.get("win_percentage"),"0"))}% · NC: {esc(clean(r.get("no_contests"),"0"))}</div>',unsafe_allow_html=True)
                    with st.expander(f"Career details · {name}"):
                        st.write(f"Debut: {datefmt(r.get('debut_date'))}")
                        st.write(f"Departure: {datefmt(r.get('departure_date')) if clean(r.get('departure_date')) else 'Not recorded'}")
                        st.write(f"Current / longest win streak: {clean(r.get('current_win_streak'),'0')} / {clean(r.get('longest_win_streak'),'0')}")
                        st.write(f"Average / highest rating: {clean(r.get('average_match_rating'),'Not rated')} / {clean(r.get('highest_match_rating'),'Not rated')}")
                        if not history.empty and "wrestler_id" in history:
                            h=history[history.wrestler_id.astype(str)==str(r.get("wrestler_id"))].copy()
                            st.markdown("Recent match history")
                            sortcols=[c for c in ["event_date","match_number"] if c in h]
                            if sortcols: h=h.sort_values(sortcols,ascending=[False]*len(sortcols),na_position="last")
                            for _,mr in h.head(5).iterrows(): match_card(mr)
                    st.markdown('</div>', unsafe_allow_html=True)

elif page == "Events & FUSION":
    st.markdown("## Events & FUSION"); st.caption("Browse the CEW calendar by event and show type.")
    if matches.empty: st.info("No event records found.")
    else:
        ev=matches.copy(); side=st.selectbox("Show category",["All","FUSION","PPV","Other"])
        if side!="All" and "side" in ev:
            ev=ev[~ev.side.astype(str).str.upper().isin(["FUSION","PPV"])] if side=="Other" else ev[ev.side.astype(str).str.upper()==side]
        if all(c in ev for c in ["event","event_date","side","venue","id"]):
            summary=ev.groupby(["event","event_date","side","venue"],dropna=False).agg(Matches=("id","count")).reset_index().sort_values("event_date",ascending=False,na_position="last")
            for _,e in summary.iterrows():
                en=clean(e.get("event"),"Unnamed event")
                with st.expander(f"{en} · {datefmt(e.get('event_date'))} · {clean(e.get('Matches'),'0')} matches"):
                    st.write(f"Show: {clean(e.get('side'),'—')} | Venue: {clean(e.get('venue'),'Not recorded')}")
                    subset=ev[ev.event.astype(str)==en]
                    subset=subset[subset.event_date.astype(str)==str(clean(e.get("event_date")))]
                    if "match_number" in subset: subset=subset.sort_values("match_number")
                    for _,r in subset.iterrows(): match_card(r)
        else: st.info("The event fields required to group episodes are not available.")
elif page == "Championships":
    st.markdown("## 🏆 CEW Championships")
    st.caption("The gold standard of Continental Elite Wrestling.")
    
    champs = table(tables, "Championships")
    reigns = table(tables, "title_reigns")
    defenses = table(tables, "title_defenses")
    
    if champs.empty:
        st.info("No championships found in the database.")
    else:
        for _, c in champs.iterrows():
            title_id = c.get("id")
            title_name = clean(c.get("title_name"), "Unknown Title")
            current_champ_id = c.get("current_champion_id")
            
            # Find the active reign for this title
            active_reign = reigns[(reigns["championship_id"] == title_id) & (reigns["status"] == "Active")]
            
            st.markdown(f"### {title_name}")
            
            if active_reign.empty or pd.isna(current_champ_id):
                st.info("Champion not yet crowned.")
            else:
                reign = active_reign.iloc[0]
                won_event = clean(reign.get("won_event"), "Unknown Event")
                won_date = datefmt(reign.get("won_date"))
                days_held = clean(reign.get("days_held"), "0")
                
                # --- HYBRID DISPLAY LOGIC ---
                champ_name = wrestler_name_by_id.get(str(current_champ_id), "Unknown Champion")
                champ_subtitle = ""
                
                if title_id == 5: # Tag Team Title
                    champ_name = "RASCALZ"
                    champ_subtitle = '<div style="color:#9ca3af; font-size:0.85rem; margin-top:2px;">Dezmond Xavier, Zachary Wentz & Myron Reed</div>'
                
                # Current Champion Display
                st.markdown(
                    f'<div class="profile-card">'
                    f'<div class="profile-name">👑 {esc(champ_name)}</div>'
                    f'{champ_subtitle}'
                    f'<div class="profile-sub">Won at {esc(won_event)} on {esc(won_date)} · <b>{esc(days_held)} Days Held</b></div>'
                    f'</div>', 
                    unsafe_allow_html=True
                )
                
                # Defenses Dropdown
                champ_defenses = defenses[defenses["reign_id"] == reign.get("id")]
                with st.expander(f"🛡️ View Defenses ({len(champ_defenses)})"):
                    if champ_defenses.empty:
                        st.write("No defenses recorded yet.")
                    else:
                        for _, d in champ_defenses.iterrows():
                            st.write(f"• **{clean(d.get('event_date'))}** at **{clean(d.get('event_name'))}** — {clean(d.get('match_time'))} mins — ⭐ {clean(d.get('star_rating'))}")
            
            # History Dropdown
            with st.expander("📜 View Full Title History"):
                title_reigns = reigns[reigns["championship_id"] == title_id].sort_values("won_date")
                if title_reigns.empty:
                    st.write("No history recorded.")
                else:
                    for _, r in title_reigns.iterrows():
                        r_champ = wrestler_name_by_id.get(str(r.get("champion_id")), "Unknown")
                        
                        # History Hybrid Display
                        if title_id == 5:
                            if r.get("champion_id") == 4: # Dezmond
                                r_champ = "RASCALZ (Dezmond, Wentz, Myron)"
                            elif r.get("champion_id") == 1: # Gabe Kidd for DOGS
                                r_champ = "DOGS (Gabe Kidd & Clark Connors)"
                                
                        r_status = clean(r.get("status"), "Ended")
                        r_won = datefmt(r.get("won_date"))
                        r_lost = datefmt(r.get("lost_date")) if clean(r.get("lost_date")) else "Current"
                        r_days = clean(r.get("days_held"), "0")
                        
                        st.markdown(f"**{esc(r_champ)}** ({r_won} - {r_lost}) — {r_days} Days — *{esc(r_status)}*")
            
            st.divider()
elif page == "Teams & Factions":
    st.markdown("## Teams & Factions")
    st.caption("Tag Teams and Factions pulled directly from the CEW archive.")

    # --- IMAGE MAPPING (Matched exactly to your GitHub filenames) ---
    def get_team_logo(name):
        name_lower = name.lower()
        if "dogs" in name_lower: return "DOGS.png"
        if "don callis" in name_lower or "dcf" in name_lower: return "DCF.png"
        if "death juries" in name_lower: return "DEATH JURIES.png"
        if "fraxiom" in name_lower: return "FRAXIOM.png"
        if "neo genesis" in name_lower: return "NEO GENESIS.png"
        if "krieger" in name_lower: return "KRIEGER.png"
        if "grizzled" in name_lower or "gyv" in name_lower: return "GYV.png"
        if "sinner" in name_lower: return "SINNER & SAINTS.png"
        if "rascalz" in name_lower: return "RASCALZ.png"
        if "vanity" in name_lower: return "VANITY PROJECT.png"
        return None

        # --- HELPER TO RENDER LOGO OR PLACEHOLDER ---
    def render_logo(name, logo_file):
        import base64, os
        if logo_file and os.path.exists(logo_file): return f'<img src="data:image/png;base64,{base64.b64encode(open(logo_file, "rb").read()).decode()}" style="width: 100%; max-height: 120px; object-fit: contain; margin-bottom: 15px;">'
        return f'<div style="background: #1f2229; padding: 20px; text-align: center; color: #6b7280; font-family: Barlow Condensed; font-weight: 700; font-size: 1.2rem; margin-bottom: 15px;">{esc(name).upper()}</div>'

        # --- FETCH FACTIONS ---
    all_factions = []
    if not factions.empty:
        for _, r in factions.sort_values("faction_name").iterrows():
            all_factions.append({
                "name": clean(r.get("faction_name"), "Unnamed faction"),
                "status": clean(r.get("status"), "ACTIVE" if clean(r.get("active"), "0") == "1" else "FORMER / INACTIVE"),
                "members": group_members(faction_members, r.get("id"), "faction_id"),
                "notes": clean(r.get("notes"))
            })
    # --- FETCH TEAMS ---
    all_teams = []
    if not teams.empty:
        for _, r in teams.sort_values("team_name").iterrows():
            all_teams.append({
                "name": clean(r.get("team_name"), "Unnamed team"),
                "status": clean(r.get("status"), "ACTIVE" if clean(r.get("active"), "0") == "1" else "FORMER / INACTIVE"),
                "members": group_members(team_members, r.get("id"), "team_id"),
                "notes": clean(r.get("notes"))
            })

    left, right = st.columns(2)

    # --- LEFT COLUMN: TAG TEAMS ---
    # --- LEFT COLUMN: TAG TEAMS ---
    with left:
        st.markdown("### Teams")
        if not all_teams:
            st.info("No tag teams recorded.")
        else:
            for g in all_teams:
                m_list = g["members"] if g["members"] else ["None"]
                logo_file = get_team_logo(g["name"])
                
                with st.container():
                    if logo_file:
                        import base64
                        try:
                            with open(logo_file, "rb") as f:
                                encoded = base64.b64encode(f.read()).decode()
                            st.markdown(f'<div style="text-align:center;"><img src="data:image/png;base64,{encoded}" style="width: 100%; border-radius: 8px; margin-bottom: 10px;"></div>', unsafe_allow_html=True)
                        except Exception:
                            st.markdown(f'<div style="background: #1f2229; padding: 20px; text-align: center; font-weight: 700; color: #6b7280;">{esc(g["name"]).upper()}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div style="background: #1f2229; padding: 20px; text-align: center; font-weight: 700; color: #6b7280;">{esc(g["name"]).upper()}</div>', unsafe_allow_html=True)
                    
                    st.markdown(f"<div style='text-align:center; font-size:1.1rem; font-weight:700; margin-bottom:5px;'>{'<br>'.join(esc(m) for m in m_list)}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align:center; color:#9ca3af; font-size:0.85rem; border-top:1px solid #30323b; padding-top:8px;'>{esc(g['status'])}</div>", unsafe_allow_html=True)
                    st.divider()

    # --- RIGHT COLUMN: FACTIONS ---
    with right:
        st.markdown("### Factions")
        if not all_factions:
            st.info("No faction records found.")
        else:
            for g in all_factions:
                m_list = g["members"] if g["members"] else ["None"]
                logo_file = get_team_logo(g["name"])
                
                with st.container():
                    if logo_file:
                        import base64
                        try:
                            with open(logo_file, "rb") as f:
                                encoded = base64.b64encode(f.read()).decode()
                            st.markdown(f'<div style="text-align:center;"><img src="data:image/png;base64,{encoded}" style="width: 100%; border-radius: 8px; margin-bottom: 10px;"></div>', unsafe_allow_html=True)
                        except Exception:
                            st.markdown(f'<div style="background: #1f2229; padding: 20px; text-align: center; font-weight: 700; color: #6b7280;">{esc(g["name"]).upper()}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div style="background: #1f2229; padding: 20px; text-align: center; font-weight: 700; color: #6b7280;">{esc(g["name"]).upper()}</div>', unsafe_allow_html=True)
                    
                    st.markdown(f"<div style='text-align:center; font-size:1.1rem; font-weight:700; margin-bottom:5px;'>{'<br>'.join(esc(m) for m in m_list)}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='text-align:center; color:#9ca3af; font-size:0.85rem; border-top:1px solid #30323b; padding-top:8px;'>{esc(g['status'])}</div>", unsafe_allow_html=True)
                    st.divider()
elif page == "Data Review":
    st.markdown("## Data Review"); st.caption("Review flags are read from the database; this page does not auto-correct records.")
    flagged=matches.copy()
    if "review_required" in flagged: flagged=flagged[flagged.review_required.fillna(0).astype(str).isin(["1","True","true"])]
    audit=table(tables,"participant_audit"); a,b=st.columns(2)
    with a: metric("Matches flagged",len(flagged),True)
    with b: metric("Participant audit issues",len(audit))
    if not flagged.empty:
        st.markdown("### Matches requiring review")
        for _,r in flagged.iterrows():
            match_card(r)
            if clean(r.get("review_reason")): st.caption(f"Review note: {clean(r.get('review_reason'))}")
    else: st.success("No matches are currently flagged through the match-level review field.")
    if not audit.empty: st.markdown("### Participant audit log"); st.dataframe(audit,use_container_width=True,hide_index=True)

elif page == "Match Importer":
    st.markdown("## 🔥 Bulk Match Importer")
    st.info("Paste your Excel rows below. Format: Event, Date, Crowd, Venue, Match Card, Result, Match Type, Notes, Finish, Time, Rating, Commentary")

    # Safety check
    if not IMPORT_ENABLED or WORKING_DATABASE is None:
        st.error("Importer disabled. Ensure working database is present.")
        st.stop()

    if "incinerator_pending_matches" not in st.session_state:
        st.session_state["incinerator_pending_matches"] = []
    pending = st.session_state["incinerator_pending_matches"]

    # --- BULK PASTE BOX ---
    with st.form("bulk_importer", clear_on_submit=True):
        bulk_text = st.text_area("Paste Excel Data Here (Tab-Separated)", height=200)
        submit_bulk = st.form_submit_button("PARSE & ADD TO QUEUE", use_container_width=True)
        
        if submit_bulk and bulk_text.strip():
            lines = bulk_text.strip().split('\n')
            added_count = 0
            for line in lines:
                # Split by tab
                parts = [p.strip() for p in line.split('\t')]
                if len(parts) >= 12:
                    # Extract fields based on your Excel format
                    event = parts[0]
                    event_date = parts[1]
                    crowd = parts[2]
                    venue = parts[3]
                    match_card = parts[5]
                    result_text = parts[6]
                    match_type = parts[7]
                    note = parts[8] if len(parts) > 8 else ""
                    finish = parts[9] if len(parts) > 9 else ""
                    match_time = parts[10] if len(parts) > 10 else ""
                    rating_text = parts[11] if len(parts) > 11 else ""
                    commentary = parts[12] if len(parts) > 12 else "Mauro Ranallo & Don Callis"

                    # Determine Winner (assuming Result Text matches a wrestler name in DB)
                    # We will try to match the result text to a wrestler
                    pending.append({
                        "event": event, "event_date": event_date, "crowd": crowd, "venue": venue,
                        "match_card": match_card, "result": result_text, "match_type": match_type,
                        "note": note, "finish": finish, "match_time": match_time,
                        "rating": float(rating_text) if rating_text.replace('.','',1).isdigit() else None,
                        "commentary": commentary, "side": "FUSION" if "EP" in event else "PPV"
                    })
                    added_count += 1
            if added_count > 0:
                st.success(f"Added {added_count} matches to the queue!")
                st.rerun()

    # --- PENDING QUEUE DISPLAY ---
    if pending:
        st.markdown("### 📋 Pending Matches")
        for idx, item in enumerate(pending):
            st.write(f"{idx+1}. **{item['event']}** | {item['match_card']} | Winner: {item['result']}")
        
        if st.button("CLEAR QUEUE", type="secondary"):
            st.session_state["incinerator_pending_matches"] = []
            st.rerun()

        st.divider()
        st.warning("⚠️ Clicking Import will save these matches AND automatically update wrestler stats.")
        confirm_batch = st.checkbox("I confirm these matches are correct.")
        
        if st.button("CONFIRM IMPORT & CALCULATE STATS", type="primary", use_container_width=True):
            if not confirm_batch:
                st.error("Please check the confirmation box.")
            else:
                try:
                    with sqlite3.connect(str(WORKING_DATABASE), timeout=10) as conn:
                        conn.execute("PRAGMA foreign_keys=ON")
                        conn.execute("BEGIN IMMEDIATE")
                        
                        # 1. GET NEXT MATCH NUMBER
                        next_num = conn.execute("SELECT COALESCE(MAX(match_number), 0) + 1 FROM matches").fetchone()[0]
                        
                        for offset, item in enumerate(pending):
                            # Insert Match
                            cur = conn.execute(
                                """INSERT INTO matches (match_number, side, event, event_date, crowd, venue, match_time, match_card, result, match_type, finish, rating, commentary, review_required, review_reason)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (next_num + offset, item["side"], item["event"], item["event_date"] or None,
                                 item["crowd"] or None, item["venue"] or None, item["match_time"] or None,
                                 item["match_card"], item["result"] or "Unknown", item["match_type"], item["finish"] or None,
                                 item["rating"], item["commentary"], 0, None) # 0 = No review needed
                            )
                            match_id = cur.lastrowid

                            # 2. AUTO-STATS CALCULATION (The Magic Part)
                            # We try to find the winner name in the result text
                            # If Result is "DOGS", we need to map "DOGS" to specific wrestlers
                            # For simplicity, we check if any wrestler's name is in the result text
                            all_wrestlers = conn.execute("SELECT id, canonical_name FROM wrestlers").fetchall()
                            
                            for w_id, w_name in all_wrestlers:
                                # If the wrestler's name is in the result text, they get a win
                                if w_name.lower() in item["result"].lower():
                                    # Update Wrestler Profile (Wins)
                                    conn.execute("""
                                        UPDATE wrestler_profiles 
                                        SET wins = COALESCE(wins, 0) + 1,
                                            total_matches = COALESCE(total_matches, 0) + 1,
                                            current_win_streak = COALESCE(current_win_streak, 0) + 1
                                        WHERE wrestler_id = ?
                                    """, (w_id,))
                                    # Insert Match Participant (Winner)
                                    conn.execute(
                                        "INSERT INTO match_participants (match_id, side_no, wrestler_id, result, parse_status) VALUES (?, ?, ?, ?, ?)",
                                        (match_id, 1, w_id, "win", "manual_verified")
                                    )
                                # If their name is in the match card but NOT the result text, they get a loss
                                elif w_name.lower() in item["match_card"].lower():
                                    conn.execute("""
                                        UPDATE wrestler_profiles 
                                        SET losses = COALESCE(losses, 0) + 1,
                                            total_matches = COALESCE(total_matches, 0) + 1,
                                            current_win_streak = 0
                                        WHERE wrestler_id = ?
                                    """, (w_id,))
                                    conn.execute(
                                        "INSERT INTO match_participants (match_id, side_no, wrestler_id, result, parse_status) VALUES (?, ?, ?, ?, ?)",
                                        (match_id, 2, w_id, "loss", "manual_verified")
                                    )
                                    
                        conn.commit()
                    
                    st.session_state["incinerator_pending_matches"] = []
                    st.cache_data.clear()
                    st.success("Batch Imported and Stats Calculated!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Import failed: {e}")
    else:
        st.info("Queue is empty. Paste your Excel data above to begin.")
st.markdown('<div style="text-align:center;color:#6b7280;font-size:.78rem;letter-spacing:1px">🔥 INCINERATOR · CEW RECORDS<br>WORKING COPY PROTECTION · VERIFIED IMPORTS ONLY</div>',unsafe_allow_html=True)

