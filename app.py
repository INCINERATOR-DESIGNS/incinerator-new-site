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

DB_CANDIDATES = [
    BASE_DIR / "incinerator_working_championships.db",
    BASE_DIR / "INCINERATOR_WORKING_COPY.db",
    BASE_DIR / "incinerator_working.db",
    BASE_DIR / "incinerator.db",
]

if os.environ.get("INCINERATOR_DB_PATH"):
    DATABASE = Path(os.environ["INCINERATOR_DB_PATH"]).expanduser().resolve()
else:
    DATABASE = next(
        (path.resolve() for path in DB_CANDIDATES if path.is_file()),
        (BASE_DIR / "incinerator.db").resolve(),
    )

LOGO_PATH = BASE_DIR / "assets" / "INCINERATOR.jpg"

IMPORT_ENABLED = os.environ.get("INCINERATOR_ENABLE_IMPORTER", "1") == "1"


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
    
    pages = ["Dashboard", "Match Explorer", "Wrestler Directory", "Events & FUSION", "Teams & Factions", "Data Review"]
    if IMPORT_ENABLED: pages.append("Match Importer")
    
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

elif page == "Teams & Factions":
    st.markdown("## Teams & Factions")
    st.caption("Confirmed memberships are separated from planned teams, future factions, and planned recruitment.")
    left,right=st.columns(2)
    with left:
        st.markdown("### Teams")
        if teams.empty: st.info("No teams recorded.")
        else:
            for _,r in teams.sort_values("team_name").iterrows():
                status = clean(r.get("status"), "ACTIVE" if clean(r.get("active"),"0")=="1" else "FORMER / INACTIVE")
                members = group_members(team_members, r.get("id"), "team_id")
                members_html = "<br>".join(esc(m) for m in members) if members else "Memberships not recorded"
                notes = clean(r.get("notes"))
                notes_html = f'<div style="margin-top:8px;color:#9ca3af;font-size:.8rem">{esc(notes)}</div>' if notes else ""
                st.markdown(f'<div class="profile-card"><div style="float:right" class="profile-sub">{esc(status)}</div><div class="profile-name">{esc(clean(r.get("team_name"),"Unnamed team"))}</div><div class="profile-sub">Debut: {esc(datefmt(r.get("debut_date")))} · End: {esc(datefmt(r.get("end_date")) if clean(r.get("end_date")) else "Not recorded")}</div><div style="margin-top:10px;font-size:.85rem"><b>MEMBERS</b><br>{members_html}</div>{notes_html}</div>',unsafe_allow_html=True)
    with right:
        st.markdown("### Factions")
        if factions.empty: st.info("No faction records have been entered yet.")
        else:
            for _,r in factions.sort_values("faction_name").iterrows():
                status = clean(r.get("status"), "ACTIVE" if clean(r.get("active"),"0")=="1" else "FORMER / INACTIVE")
                members = group_members(faction_members, r.get("id"), "faction_id")
                members_html = "<br>".join(esc(m) for m in members) if members else "Memberships not recorded"
                notes = clean(r.get("notes"))
                notes_html = f'<div style="margin-top:8px;color:#9ca3af;font-size:.8rem">{esc(notes)}</div>' if notes else ""
                st.markdown(f'<div class="profile-card"><div style="float:right" class="profile-sub">{esc(status)}</div><div class="profile-name">{esc(clean(r.get("faction_name"),"Unnamed faction"))}</div><div style="margin-top:10px;font-size:.85rem"><b>MEMBERS</b><br>{members_html}</div>{notes_html}</div>',unsafe_allow_html=True)

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
    st.markdown("## 🔥 Match Importer")
    st.warning(
        "WORKING COPY ONLY. Matches are queued first and are not saved until you confirm the batch. "
        "Imported records remain flagged for review; career statistics are not recalculated automatically."
    )

    
# Fail closed: importer requires explicit opt-in and a working-copy database.
safe_working_db = "working" in DATABASE.name.lower()

if not IMPORT_ENABLED or not safe_working_db:
    st.error(
        "Importer disabled for safety. The importer requires "
        "INCINERATOR_ENABLE_IMPORTER=1 and a database filename "
        "containing 'working'."
    )
    st.stop()


    wrestlers_for_import = table(tables, "wrestlers").copy()
    if wrestlers_for_import.empty:
        st.error("The wrestlers table is empty; import is disabled.")
    else:
        wrestler_rows = wrestlers_for_import.sort_values("canonical_name")
        names = {
            str(r.canonical_name): int(r.id)
            for _, r in wrestler_rows.iterrows()
            if clean(r.get("canonical_name")) and pd.notna(r.get("id"))
        }

        if "incinerator_pending_matches" not in st.session_state:
            st.session_state["incinerator_pending_matches"] = []

        pending = st.session_state["incinerator_pending_matches"]

        with st.form("real_match_importer", clear_on_submit=True):
            st.subheader("Event details")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                event = st.text_input("FUSION EP / Event *", placeholder="FUSION EP 31")
            with c2:
                event_date = st.text_input("Date", placeholder="27 JUN 2027")
            with c3:
                crowd = st.text_input("Crowd")
            with c4:
                venue = st.text_input("Venue")

            c1, c2, c3 = st.columns(3)
            with c1:
                side = st.selectbox("Show category", ["FUSION", "PPV", "Other"])
            with c2:
                match_type = st.selectbox(
                    "Match type",
                    ["Single", "Tag Team", "6 Woman Tag Team Match", "Triple Threat",
                     "Fatal 4-Way", "Battle Royal", "Segment", "Other"]
                )
            with c3:
                commentary = st.selectbox(
                    "Commentary team",
                    ["Mauro Ranallo + Don Callis", "Mauro Ranallo + Kevin Kelly",
                     "Mauro Ranallo + Don Callis + Kevin Kelly"]
                )

            card = st.text_area(
                "Match card / segment description *",
                placeholder="RASCALZ (TREY MIGUEL & DEZMOND XAVIER) VS DOGS (CLARK CONNORS & GABE KIDD)",
                height=90
            )
            c1, c2, c3 = st.columns(3)
            with c1:
                result = st.text_input("Result text", placeholder="Rascals defeated Dogs")
            with c2:
                finish = st.text_input("Via / finish", placeholder="Pinfall")
            with c3:
                match_time = st.text_input("Match time", placeholder="19:17")
            note = st.text_input("Match note (optional)")

            st.subheader("Link participants explicitly")
            st.caption("Choose each wrestler from the database. Leave both participant lists empty for a segment.")
            c1, c2 = st.columns(2)
            with c1:
                side_a = st.multiselect("Side A / first wrestler(s)", list(names))
            with c2:
                side_b = st.multiselect("Side B / opposing wrestler(s)", list(names))

            outcome = st.selectbox(
                "Validated outcome",
                ["Needs review / unknown", "Side A wins", "Side B wins", "Draw",
                 "No contest", "Segment / no wrestler result"]
            )
            rating_text = st.text_input("Star rating (leave blank for unrated)", placeholder="4.25 or 5.25")
            confirm = st.checkbox("I checked the event and participant names, and match is good to go for INCINERATOR.")
            add_to_queue = st.form_submit_button("ADD MATCH TO PENDING QUEUE", use_container_width=True)

        if add_to_queue:
            errors = []
            if not event.strip():
                errors.append("Event name is required.")
            if not card.strip():
                errors.append("Match card / segment description is required.")
            if not confirm:
                errors.append("Confirm the duplicate/name check before adding this match.")
            if set(side_a) & set(side_b):
                errors.append("A wrestler cannot be on both sides.")
            if match_type != "Segment" and outcome not in {"Segment / no wrestler result", "Needs review / unknown"} and (not side_a or not side_b):
                errors.append("Choose participants for both sides before recording a match outcome.")
            try:
                rating = float(rating_text) if rating_text.strip() else None
                if rating is not None and rating < 0:
                    errors.append("Rating must be zero or higher.")
            except ValueError:
                rating = None
                errors.append("Rating must be a number, or blank for unrated.")

            if errors:
                for error in errors:
                    st.error(error)
            else:
                duplicate_in_queue = any(
                    item["event"].strip().casefold() == event.strip().casefold()
                    and item["match_card"].strip().casefold() == card.strip().casefold()
                    for item in pending
                )
                existing_duplicate = False
                if not matches.empty and {"event", "match_card"}.issubset(matches.columns):
                    existing_duplicate = not matches[
                        (matches.event.fillna("").astype(str).str.casefold() == event.strip().casefold())
                        & (matches.match_card.fillna("").astype(str).str.casefold() == card.strip().casefold())
                    ].empty

                if duplicate_in_queue or existing_duplicate:
                    st.error("Possible duplicate found in the pending queue or database. Check before adding.")
                else:
                    pending.append({
                        "event": event.strip(), "event_date": event_date.strip(),
                        "crowd": crowd.strip(), "venue": venue.strip(), "side": side,
                        "match_type": match_type, "commentary": commentary,
                        "match_card": card.strip(), "result": result.strip(), "finish": finish.strip(),
                        "match_time": match_time.strip(), "note": note.strip(),
                        "side_a": list(side_a), "side_b": list(side_b), "outcome": outcome,
                        "rating": rating
                    })
                    st.success(f"Added to pending queue. {len(pending)} match(es) waiting; nothing has been written to the database.")

        st.markdown("## 📋 Pending Matches")
        if not pending:
            st.info("Your pending queue is empty. Add a match above to begin.")
        else:
            st.caption(f"{len(pending)} match(es) queued in this session. They are not saved yet.")
            for idx, item in enumerate(pending):
                with st.expander(f"{idx + 1}. {item['event']} · {item['match_card']}", expanded=False):
                    st.write(f"**Date:** {item['event_date'] or 'Not entered'} · **Type:** {item['match_type']}")
                    st.write(f"**Result choice:** {item['outcome']} · **Rating:** {item['rating'] if item['rating'] is not None else 'Unrated'}")
                    st.write(f"**Side A:** {', '.join(item['side_a']) or 'None'}")
                    st.write(f"**Side B:** {', '.join(item['side_b']) or 'None'}")
                    st.caption("To change a queued match, remove it and add it again with the corrected details.")
                    if st.button("REMOVE FROM QUEUE", key=f"remove_pending_{idx}"):
                        pending.pop(idx)
                        st.rerun()

            st.warning("Confirming imports all queued matches together. If any insert fails, the entire database transaction is rolled back.")
            confirm_batch = st.checkbox("I reviewed every queued match and confirmed the batch is ready for import.", key="confirm_incinerator_batch")
            if st.button("CONFIRM IMPORT — SAVE ENTIRE BATCH", type="primary", use_container_width=True):
                if not confirm_batch:
                    st.error("Please confirm that you reviewed the entire batch.")
                else:
                    try:
                        if not IMPORT_ENABLED or "working" not in DATABASE.name.lower():
                            raise RuntimeError("Safety check failed: refusing to write to a non-working database.")
                        with sqlite3.connect(str(DATABASE), timeout=10) as conn:
                            conn.execute("PRAGMA foreign_keys=ON")
                            conn.execute("BEGIN IMMEDIATE")
                            match_cols = {row[1] for row in conn.execute("PRAGMA table_info(matches)")}
                            required_match_cols = {
                                "match_number", "side", "event", "event_date", "crowd", "venue",
                                "match_time", "match_card", "result", "match_type", "finish",
                                "rating", "commentary", "review_required", "review_reason"
                            }
                            if not required_match_cols.issubset(match_cols):
                                raise RuntimeError("The matches table schema does not match the expected importer schema.")
                            participant_cols = {row[1] for row in conn.execute("PRAGMA table_info(match_participants)")}
                            required_participant_cols = {
                                "match_id", "side_no", "source_label", "wrestler_id", "team_name",
                                "result", "parse_status", "parse_note"
                            }
                            if not required_participant_cols.issubset(participant_cols):
                                raise RuntimeError("The match_participants table schema does not match the expected importer schema.")

                            next_num = conn.execute("SELECT COALESCE(MAX(match_number), 0) + 1 FROM matches").fetchone()[0]
                            saved = []
                            outcome_labels = {
                                "Side A wins": "Side A wins", "Side B wins": "Side B wins",
                                "Draw": "Draw", "No contest": "No contest",
                                "Segment / no wrestler result": "Segment",
                                "Needs review / unknown": "Needs review"
                            }
                            for offset, item in enumerate(pending):
                                
                                outcome = item["outcome"]
                                review_reason = (
                                    "Batch importer: participant/result review required"
                                    if outcome in {"Needs review / unknown", "Segment / no wrestler result"} or item["match_type"] == "Segment"
                                    else "Batch importer: verify before statistics refresh"
                                )
                                cur = conn.execute(
                                    """INSERT INTO matches
                                    (match_number, side, event, event_date, crowd, venue, match_time, match_card,
                                     result, match_type, finish, rating, commentary, review_required, review_reason)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                    (next_num + offset, item["side"], item["event"], item["event_date"] or None,
                                     item["crowd"] or None, item["venue"] or None, item["match_time"] or None,
                                     item["match_card"], item["result"] or outcome_labels[outcome],
                                     item["match_type"], item["finish"] or None, item["rating"],
                                     item["commentary"], 1, review_reason)
                                )
                                match_id = cur.lastrowid
                                for side_no, side_names in ((1, item["side_a"]), (2, item["side_b"])):
                                    for wrestler_name in side_names:
                                        if wrestler_name not in names:
                                            raise RuntimeError(f"Wrestler '{wrestler_name}' is no longer available in the loaded roster.")
                                        participant_result = "unknown"
                                        if outcome == "Side A wins":
                                            participant_result = "win" if side_no == 1 else "loss"
                                        elif outcome == "Side B wins":
                                            participant_result = "win" if side_no == 2 else "loss"
                                        elif outcome == "Draw":
                                            participant_result = "draw"
                                        elif outcome == "No contest":
                                            participant_result = "no contest"
                                        conn.execute(
                                            """INSERT INTO match_participants
                                            (match_id, side_no, source_label, wrestler_id, team_name, result, parse_status, parse_note)
                                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                                            (match_id, side_no, wrestler_name, names[wrestler_name], None,
                                             participant_result, "manual_verified", "Selected explicitly in batch Match Importer")
                                        )
                                if item["note"] and "participant_audit" in tables:
                                    audit_cols = {row[1] for row in conn.execute("PRAGMA table_info(participant_audit)")}
                                    if {"match_id", "issue_type", "detail", "severity"}.issubset(audit_cols):
                                        conn.execute(
                                            "INSERT INTO participant_audit(match_id, issue_type, detail, severity) VALUES (?, ?, ?, ?)",
                                            (match_id, "importer_note", item["note"], "info")
                                        )
                                saved.append((next_num + offset, match_id))
                            conn.commit()

                        st.session_state["incinerator_pending_matches"] = []
                        st.session_state["confirm_incinerator_batch"] = False
                        st.cache_data.clear()
                        st.success(f"Successfully imported {len(saved)} match(es) into {DATABASE.name}.")
                        st.warning("All imported matches remain flagged for review. Wrestler records, profiles, streaks, and match history were NOT automatically recalculated.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Batch import failed; no partial batch should have been committed. Details: {e}")

st.divider()
st.markdown('<div style="text-align:center;color:#6b7280;font-size:.78rem;letter-spacing:1px">🔥 INCINERATOR · CEW RECORDS<br>WORKING COPY PROTECTION · VERIFIED IMPORTS ONLY</div>',unsafe_allow_html=True)
