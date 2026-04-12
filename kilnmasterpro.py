import streamlit as st
import json
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import re
import base64
from supabase import create_client, Client

# ============================================================
# Page Config
# ============================================================
st.set_page_config(
    page_title="KilnMaster Pro",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# Supabase Client (cached so it only creates once per session)
# ============================================================
@st.cache_resource
def init_supabase() -> Client:
    url  = st.secrets["SUPABASE_URL"]
    key  = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# ============================================================
# Constants
# ============================================================
CONE_TEMPS = {
    '04': 1830, '03': 1850, '02': 1870, '01': 1890, '1': 1910,
    '2': 1920, '3': 1930, '4': 1945, '5': 1975, '6': 1995,
    '7': 2015, '8': 2035, '9': 2055, '10': 2075
}

CLAY_BODIES = [
    'Cone 6 Stoneware', 'Porcelain', 'Buff Stoneware', 'White Stoneware',
    'Speckled Stoneware', 'Dark Stoneware', 'Earthenware', 'Custom Mix'
]

DEFAULT_HARDWARE = {
    'elements':      {'installed': '', 'firing_count': 0, 'max_life': 300},
    'thermocouples': {'installed': '', 'firing_count': 0, 'max_life': 1000},
    'relays':        {'installed': '', 'firing_count': 0, 'max_life': 500}
}

DEFAULT_ZONE_OFFSETS = {'top': 18, 'middle': 18, 'bottom': 18}

# ============================================================
# Auth Session Helpers
# ============================================================
def _restore_session():
    """Re-attach stored tokens to the Supabase client after a Streamlit rerun."""
    access  = st.session_state.get("_access_token")
    refresh = st.session_state.get("_refresh_token")
    if access and refresh:
        try:
            supabase.auth.set_session(access, refresh)
        except Exception:
            # Tokens expired — force re-login
            _clear_auth_state()

def _store_session(session_obj):
    """Persist tokens so they survive Streamlit reruns."""
    st.session_state["_access_token"]  = session_obj.access_token
    st.session_state["_refresh_token"] = session_obj.refresh_token
    st.session_state["user"]           = session_obj.user

def _clear_auth_state():
    for key in ["_access_token", "_refresh_token", "user",
                "firings", "programs", "zone_offsets", "hardware",
                "current_page", "data_loaded"]:
        st.session_state.pop(key, None)

# ============================================================
# Auth Actions
# ============================================================
def sign_up(email: str, password: str, full_name: str):
    try:
        resp = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"full_name": full_name}}
        })
        return resp, None
    except Exception as e:
        return None, str(e)

def sign_in(email: str, password: str):
    try:
        resp = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return resp, None
    except Exception as e:
        return None, str(e)

def sign_out():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    _clear_auth_state()
    st.rerun()

# ============================================================
# Database Helpers  (all scoped to the logged-in user)
# ============================================================
def get_user_id() -> str:
    return st.session_state["user"].id

def load_user_data():
    """Pull all user data from Supabase into session_state."""
    uid = get_user_id()

    # Firings
    resp = supabase.table("firings").select("*").eq("user_id", uid).order("created_at").execute()
    st.session_state.firings = resp.data or []

    # Programs
    resp = supabase.table("programs").select("*").eq("user_id", uid).order("created_at").execute()
    st.session_state.programs = resp.data or []

    # Settings (zone offsets + hardware)
    resp = supabase.table("user_settings").select("*").eq("user_id", uid).execute()
    if resp.data:
        row = resp.data[0]
        st.session_state.zone_offsets = row.get("zone_offsets", DEFAULT_ZONE_OFFSETS)
        st.session_state.hardware     = row.get("hardware",     DEFAULT_HARDWARE)
    else:
        st.session_state.zone_offsets = DEFAULT_ZONE_OFFSETS.copy()
        st.session_state.hardware     = {k: v.copy() for k, v in DEFAULT_HARDWARE.items()}
        _save_settings()           # create the row for this new user

    st.session_state.data_loaded = True

def _save_settings():
    """Upsert zone offsets + hardware back to Supabase."""
    uid = get_user_id()
    supabase.table("user_settings").upsert(
        {
            "user_id":      uid,
            "zone_offsets": st.session_state.zone_offsets,
            "hardware":     st.session_state.hardware,
        },
        on_conflict="user_id"
    ).execute()

def add_firing(firing: dict):
    uid = get_user_id()
    firing["user_id"] = uid
    # Remove any local-only 'id' key — Supabase will generate a UUID
    firing.pop("id", None)
    resp = supabase.table("firings").insert(firing).execute()
    # Reload so local list matches DB order
    load_firings()
    return resp

def load_firings():
    uid = get_user_id()
    resp = supabase.table("firings").select("*").eq("user_id", uid).order("created_at").execute()
    st.session_state.firings = resp.data or []

def add_program(program: dict):
    uid = get_user_id()
    program["user_id"] = uid
    program.pop("id", None)
    supabase.table("programs").insert(program).execute()
    load_programs()

def load_programs():
    uid = get_user_id()
    resp = supabase.table("programs").select("*").eq("user_id", uid).order("created_at").execute()
    st.session_state.programs = resp.data or []

# ============================================================
# Business Logic Helpers
# ============================================================
def calculate_suggested_offsets():
    if len(st.session_state.firings) == 0:
        return None

    recent = st.session_state.firings[-5:]
    suggestions = {}

    for zone in ['top', 'middle', 'bottom']:
        total_adj, valid = 0, 0
        for f in recent:
            zr     = f.get('zone_results') or {}
            result = (zr.get(zone) or f.get('actual_result', '')).lower()
            target = int(f.get('target_cone', 6))

            if 'cone' in result:
                if 'hot' in result or 'soft' in result:
                    total_adj += 12; valid += 1
                elif 'perfect' in result or 'good' in result:
                    valid += 1
                else:
                    m = re.search(r'cone\s*(\d+)', result)
                    if m:
                        actual = int(m.group(1))
                        total_adj += (actual - target) * 18
                        valid += 1

        current = st.session_state.zone_offsets[zone]
        if valid:
            suggestions[zone] = max(0, min(100, current + round(total_adj / valid)))
        else:
            suggestions[zone] = current

    return suggestions

def get_health_status(component_data: dict) -> dict:
    pct = (component_data['firing_count'] / component_data['max_life']) * 100
    if pct < 60:
        return {'color': 'green', 'status': 'Excellent', 'emoji': '✅'}
    elif pct < 85:
        return {'color': 'orange', 'status': 'Monitor',  'emoji': '⚠️'}
    else:
        return {'color': 'red',   'status': 'Replace Soon', 'emoji': '🚨'}

def export_data() -> str:
    data = {
        'firings':      st.session_state.firings,
        'zone_offsets': st.session_state.zone_offsets,
        'hardware':     st.session_state.hardware,
        'programs':     st.session_state.programs,
        'exported':     datetime.now().isoformat()
    }
    return json.dumps(data, indent=2)

# ============================================================
# CSS
# ============================================================
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #f97316, #dc2626);
        padding: 2rem; border-radius: 1rem;
        margin-bottom: 2rem; color: white; text-align: center;
    }
    .auth-container {
        max-width: 480px; margin: 4rem auto;
        background: white; padding: 2.5rem;
        border-radius: 1rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.12);
    }
    .zone-card {
        background: linear-gradient(135deg, #3b82f6, #1d4ed8);
        color: white; padding: 1.5rem;
        border-radius: 1rem; margin: 0.5rem 0;
    }
    .stButton > button {
        background: linear-gradient(90deg, #f97316, #dc2626);
        color: white; border: none; border-radius: 0.5rem;
        font-weight: bold; transition: all 0.3s ease;
        width: 100%; padding: 0.5rem 1rem;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #ea580c, #b91c1c);
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# AUTH WALL  — shown until the user is logged in
# ============================================================
_restore_session()   # re-attach tokens after Streamlit rerun

if "user" not in st.session_state or st.session_state.user is None:

    # Centered auth UI
    st.markdown("""
    <div style="text-align:center; margin-top: 2rem;">
        <h1 style="font-size:3rem;">🔥</h1>
        <h2 style="font-size:2rem; font-weight:800; color:#dc2626;">KilnMaster Pro</h2>
        <p style="color:#6b7280;">Advanced Kiln Management & Analytics</p>
    </div>
    """, unsafe_allow_html=True)

    auth_tab1, auth_tab2 = st.tabs(["🔑 Sign In", "✨ Create Account"])

    # --- Sign In ---
    with auth_tab1:
        with st.form("signin_form"):
            st.subheader("Welcome back!")
            email    = st.text_input("Email",    placeholder="your@email.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("🔥 Sign In", use_container_width=True)

            if submitted:
                if not email or not password:
                    st.error("Please fill in both fields.")
                else:
                    with st.spinner("Signing in…"):
                        resp, err = sign_in(email, password)
                    if err:
                        st.error(f"Sign-in failed: {err}")
                    elif resp and resp.session:
                        _store_session(resp.session)
                        st.success("Signed in! Loading your data…")
                        st.rerun()
                    else:
                        st.error("Unexpected error. Please try again.")

    # --- Sign Up ---
    with auth_tab2:
        with st.form("signup_form"):
            st.subheader("Create your account")
            full_name  = st.text_input("Full Name",       placeholder="Jane Potter")
            email2     = st.text_input("Email",           placeholder="your@email.com")
            password2  = st.text_input("Password",        type="password",
                                       help="At least 6 characters")
            password2b = st.text_input("Confirm Password", type="password")
            submitted2 = st.form_submit_button("✨ Create Account", use_container_width=True)

            if submitted2:
                if not all([full_name, email2, password2, password2b]):
                    st.error("Please fill in all fields.")
                elif password2 != password2b:
                    st.error("Passwords don't match.")
                elif len(password2) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    with st.spinner("Creating your account…"):
                        resp, err = sign_up(email2, password2, full_name)
                    if err:
                        st.error(f"Sign-up failed: {err}")
                    elif resp and resp.session:
                        _store_session(resp.session)
                        st.success("Account created! Welcome to KilnMaster Pro 🔥")
                        st.rerun()
                    elif resp and resp.user:
                        # Supabase email confirmation required
                        st.success(
                            "Account created! Check your email to confirm your address, "
                            "then sign in."
                        )
                    else:
                        st.error("Unexpected error. Please try again.")

    st.stop()   # Don't render anything below until logged in


# ============================================================
# DATA LOAD  — runs once per login session
# ============================================================
if not st.session_state.get("data_loaded"):
    with st.spinner("Loading your kiln data…"):
        load_user_data()

# ============================================================
# MAIN APP HEADER
# ============================================================
st.markdown("""
<div class="main-header">
    <h1>🔥 KilnMaster Pro</h1>
    <p>Advanced Kiln Management & Analytics</p>
</div>
""", unsafe_allow_html=True)

# User info + sign-out in sidebar
user = st.session_state.user
user_name  = (user.user_metadata or {}).get("full_name", user.email)
with st.sidebar:
    st.markdown(f"### 👤 {user_name}")
    st.caption(user.email)
    st.divider()
    if st.button("🚪 Sign Out", use_container_width=True):
        sign_out()

# ============================================================
# NAVIGATION
# ============================================================
if 'current_page' not in st.session_state:
    st.session_state.current_page = "🔥 Firing Log"

st.markdown("### 🧭 Navigation")
nav_col1, nav_col2, nav_col3, nav_col4, nav_col5, nav_col6, nav_col7, export_col = st.columns([1,1,1,1,1,1,1,1])

nav_pages = [
    ("🔥 Firing Log",  nav_col1),
    ("🎯 Zone Control", nav_col2),
    ("⚙️ Programs",    nav_col3),
    ("🔧 Maintenance",  nav_col4),
    ("📊 Analytics",   nav_col5),
    ("❓ Help",        nav_col6),
    ("ℹ️ About",       nav_col7),
]

for page_name, col in nav_pages:
    with col:
        btn_type = "primary" if st.session_state.current_page == page_name else "secondary"
        if st.button(page_name, key=f"nav_{page_name}", use_container_width=True, type=btn_type):
            st.session_state.current_page = page_name

with export_col:
    if st.button("📥 Export Data", use_container_width=True):
        data_json = export_data()
        b64 = base64.b64encode(data_json.encode()).decode()
        href = (
            f'<a href="data:application/json;base64,{b64}" '
            f'download="kiln_data_{datetime.now().strftime("%Y%m%d")}.json">'
            f'Download Kiln Data</a>'
        )
        st.markdown(href, unsafe_allow_html=True)
        st.success("✅ Click the link above to download your data!")

page = st.session_state.current_page
st.divider()

# ============================================================
# PAGE: Firing Log
# ============================================================
if page == "🔥 Firing Log":
    st.header("🔥 Firing Log")

    col1, col2, col3, col4 = st.columns(4)
    offsets = st.session_state.zone_offsets
    with col1:
        st.metric("🎯 Zone Offsets",
                  f"T:{offsets['top']}° M:{offsets['middle']}° B:{offsets['bottom']}°")
    with col2:
        st.metric("📈 Total Firings", len(st.session_state.firings))
    with col3:
        el = st.session_state.hardware['elements']
        usage = round((el['firing_count'] / el['max_life']) * 100)
        st.metric("⚡ Element Health", f"{usage}%",
                  delta=f"{el['firing_count']}/{el['max_life']} firings")
    with col4:
        firings = st.session_state.firings
        if firings:
            sc = sum(1 for f in firings
                     if any(w in f.get('actual_result', '').lower()
                            for w in ['perfect', 'good']))
            rate = round((sc / len(firings)) * 100)
        else:
            rate = 0
        st.metric("🎯 Success Rate", f"{rate}%")

    # AI suggestions
    suggestions = calculate_suggested_offsets()
    if suggestions and any(suggestions[z] != st.session_state.zone_offsets[z] for z in suggestions):
        st.info("🤖 **AI Suggestions Available!** Based on your recent firings:")
        c1, c2, c3 = st.columns(3)
        for i, zone in enumerate(['top', 'middle', 'bottom']):
            with [c1, c2, c3][i]:
                if suggestions[zone] != st.session_state.zone_offsets[zone]:
                    st.write(f"**{zone.title()} Zone:** {suggestions[zone]}°F")
                    if st.button(f"Apply {zone.title()}", key=f"apply_{zone}"):
                        st.session_state.zone_offsets[zone] = suggestions[zone]
                        _save_settings()
                        st.success(f"Applied {zone} zone suggestion!")

    # Log new firing
    st.subheader("➕ Log New Firing")
    with st.form("new_firing"):
        c1, c2, c3, c4 = st.columns(4)
        with c1: target_cone  = st.selectbox("Target Cone", list(CONE_TEMPS.keys()), index=5)
        with c2: firing_type  = st.selectbox("Firing Type", ["bisque", "glaze", "test"], index=1)
        with c3: clay_body    = st.selectbox("Clay Body", [""] + CLAY_BODIES)
        with c4: load_density = st.selectbox("Load Density", ["full", "partial", "test"])

        c1, c2 = st.columns(2)
        with c1: actual_result = st.text_input("Overall Result",
                                    placeholder="e.g., 'hot cone 6', 'cone 7', 'perfect cone 6'")
        with c2: glaze_type    = st.text_input("Glaze Type (optional)",
                                    placeholder="e.g., 'Clear', 'Celadon', 'Matte Black'")

        st.write("**Zone-Specific Results (optional):**")
        c1, c2, c3 = st.columns(3)
        with c1: top_result    = st.text_input("Top Zone Result",    placeholder="Optional")
        with c2: middle_result = st.text_input("Middle Zone Result", placeholder="Optional")
        with c3: bottom_result = st.text_input("Bottom Zone Result", placeholder="Optional")

        notes     = st.text_area("Notes", placeholder="Any observations about the firing…")
        submitted = st.form_submit_button("🔥 Log Firing")

        if submitted and actual_result:
            new_firing = {
                'date':          datetime.now().strftime("%Y-%m-%d"),
                'time':          datetime.now().strftime("%H:%M:%S"),
                'zone_offsets':  st.session_state.zone_offsets.copy(),
                'target_cone':   target_cone,
                'actual_result': actual_result,
                'zone_results':  {'top': top_result, 'middle': middle_result, 'bottom': bottom_result},
                'firing_type':   firing_type,
                'clay_body':     clay_body,
                'glaze_type':    glaze_type,
                'load_density':  load_density,
                'notes':         notes,
            }
            with st.spinner("Saving firing…"):
                add_firing(new_firing)
                # Update hardware firing counts and save
                for comp in st.session_state.hardware:
                    st.session_state.hardware[comp]['firing_count'] += 1
                _save_settings()
            st.success("✅ Firing logged successfully!")

    # Recent firings
    st.subheader("📋 Recent Firings")
    if st.session_state.firings:
        for firing in reversed(st.session_state.firings[-10:]):
            with st.expander(f"{firing['date']} - {firing['firing_type'].title()} - Cone {firing['target_cone']}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Result:** {firing['actual_result']}")
                    st.write(f"**Target:** Cone {firing['target_cone']}")
                    if firing.get('clay_body'): st.write(f"**Clay Body:** {firing['clay_body']}")
                    if firing.get('glaze_type'): st.write(f"**Glaze:** {firing['glaze_type']}")
                with c2:
                    zo = firing.get('zone_offsets') or {}
                    st.write(f"**Zone Offsets:** T:{zo.get('top','?')}° M:{zo.get('middle','?')}° B:{zo.get('bottom','?')}°")
                    st.write(f"**Load:** {firing['load_density'].title()}")
                    st.write(f"**Time:** {firing['time']}")
                zr = firing.get('zone_results') or {}
                if any(zr.values()):
                    st.write("**Zone Results:**")
                    for z, r in zr.items():
                        if r: st.write(f"- {z.title()}: {r}")
                if firing.get('notes'): st.write(f"**Notes:** {firing['notes']}")
    else:
        st.info("🔥 No firings logged yet. Start by logging your first firing above!")

# ============================================================
# PAGE: Zone Control
# ============================================================
elif page == "🎯 Zone Control":
    st.header("🎯 Zone Control Center")
    st.write("Manage individual zone offsets for precise firing control")

    c1, c2, c3 = st.columns(3)
    zones  = ['top', 'middle', 'bottom']
    colors = ['🔴', '🔵', '🟢']
    changed = False

    for i, zone in enumerate(zones):
        with [c1, c2, c3][i]:
            st.markdown(f"""
            <div class="zone-card">
                <h3>{colors[i]} {zone.title()} Zone</h3>
                <div style="font-size:2rem;font-weight:bold;">
                    {st.session_state.zone_offsets[zone]}°F
                </div>
            </div>""", unsafe_allow_html=True)

            new_val = st.number_input(f"{zone.title()} Zone Offset (°F)",
                                      min_value=0, max_value=100,
                                      value=st.session_state.zone_offsets[zone],
                                      key=f"offset_{zone}")
            if new_val != st.session_state.zone_offsets[zone]:
                st.session_state.zone_offsets[zone] = new_val
                changed = True

    if changed:
        _save_settings()
        st.success("✅ Zone offsets saved to your account!")

    if st.session_state.firings:
        st.subheader("📊 Recent Zone Performance")
        data = []
        for f in st.session_state.firings[-5:]:
            zo = f.get('zone_offsets') or {}
            for z in ['top', 'middle', 'bottom']:
                data.append({'Date': f['date'], 'Zone': z.title(), 'Offset': zo.get(z, 0)})
        if data:
            fig = px.line(pd.DataFrame(data), x='Date', y='Offset', color='Zone',
                          title="Zone Offset Trends", markers=True)
            st.plotly_chart(fig, use_container_width=True)

# ============================================================
# PAGE: Programs
# ============================================================
elif page == "⚙️ Programs":
    st.header("⚙️ Firing Programs")

    st.subheader("➕ Create New Program")
    with st.form("new_program"):
        c1, c2, c3, c4 = st.columns(4)
        with c1: program_name = st.text_input("Program Name", placeholder="e.g., Cone 6 Slow Glaze")
        with c2: program_type = st.selectbox("Type", ["bisque", "glaze", "test"])
        with c3: target_temp  = st.number_input("Target Temp (°F)", value=2165)
        with c4: ramp_rate    = st.number_input("Ramp Rate (°F/hr)", value=150)

        c1, c2 = st.columns(2)
        with c1: hold_time       = st.number_input("Hold Time (min)", value=10)
        with c2: recommended_clay = st.selectbox("Recommended Clay", [""] + CLAY_BODIES)

        program_notes = st.text_area("Program Notes", placeholder="Special instructions or notes…")
        submitted = st.form_submit_button("💾 Save Program")

        if submitted and program_name:
            new_program = {
                'name':       program_name,
                'type':       program_type,
                'target_temp': int(target_temp),
                'ramp_rate':  int(ramp_rate),
                'hold_time':  int(hold_time),
                'clay_body':  recommended_clay,
                'notes':      program_notes,
            }
            with st.spinner("Saving program…"):
                add_program(new_program)
            st.success("✅ Program saved!")

    st.subheader("📚 Saved Programs")
    if st.session_state.programs:
        for p in st.session_state.programs:
            with st.expander(f"{p['name']} ({p['type'].title()})"):
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Target:** {p['target_temp']}°F")
                    st.write(f"**Ramp Rate:** {p['ramp_rate']}°F/hr")
                    st.write(f"**Hold Time:** {p['hold_time']} min")
                with c2:
                    st.write(f"**Type:** {p['type'].title()}")
                    created = p.get('created_at', '')[:10] if p.get('created_at') else '—'
                    st.write(f"**Created:** {created}")
                    if p.get('clay_body'): st.write(f"**Recommended Clay:** {p['clay_body']}")
                if p.get('notes'): st.write(f"**Notes:** {p['notes']}")
    else:
        st.info("📚 No programs saved yet. Create your first firing program above!")

# ============================================================
# PAGE: Maintenance
# ============================================================
elif page == "🔧 Maintenance":
    st.header("🔧 Hardware Maintenance")
    st.write("Monitor and maintain your kiln components")

    components      = ['elements', 'thermocouples', 'relays']
    component_names = ['Elements', 'Thermocouples', 'Relays']
    hw_changed      = False

    for i, component in enumerate(components):
        data   = st.session_state.hardware[component]
        health = get_health_status(data)
        usage  = round((data['firing_count'] / data['max_life']) * 100)

        st.subheader(f"{health['emoji']} {component_names[i]}")
        c1, c2, c3 = st.columns(3)

        with c1:
            installed_val = (datetime.fromisoformat(data['installed']).date()
                             if data['installed'] else date.today())
            new_date = st.date_input(f"{component_names[i]} Install Date",
                                     value=installed_val, key=f"install_{component}")
            new_iso = new_date.isoformat()
            if new_iso != data['installed']:
                st.session_state.hardware[component]['installed'] = new_iso
                hw_changed = True

        with c2:
            new_count = st.number_input(f"{component_names[i]} Firing Count",
                                        min_value=0, value=data['firing_count'],
                                        key=f"count_{component}")
            if new_count != data['firing_count']:
                st.session_state.hardware[component]['firing_count'] = new_count
                hw_changed = True

        with c3:
            new_max = st.number_input(f"{component_names[i]} Expected Life",
                                      min_value=1, value=data['max_life'],
                                      key=f"life_{component}")
            if new_max != data['max_life']:
                st.session_state.hardware[component]['max_life'] = new_max
                hw_changed = True

        st.write(f"**Usage:** {usage}% - {health['status']}")
        st.progress(min(usage / 100, 1.0))

        if usage >= 85:   st.error(f"🚨 {component_names[i]} replacement recommended! ({usage}% used)")
        elif usage >= 60: st.warning(f"⚠️ Monitor {component_names[i]} closely. ({usage}% used)")
        else:             st.success(f"✅ {component_names[i]} in excellent condition. ({usage}% used)")
        st.divider()

    if hw_changed:
        _save_settings()

# ============================================================
# PAGE: Analytics
# ============================================================
elif page == "📊 Analytics":
    st.header("📊 Firing Analytics")

    if not st.session_state.firings:
        st.info("📊 No data available yet. Log some firings to see analytics!")
    else:
        firings = st.session_state.firings

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            sc = sum(1 for f in firings
                     if any(w in f.get('actual_result','').lower()
                            for w in ['perfect', 'good']))
            st.metric("🎯 Success Rate", f"{round((sc/len(firings))*100)}%")
        with c2:
            avg = round(sum(f.get('zone_offsets',{}).get('middle', 18) for f in firings) / len(firings))
            st.metric("🌡️ Avg Middle Offset", f"{avg}°F")
        with c3:
            cc = {}
            for f in firings:
                if f.get('clay_body'):
                    cc[f['clay_body']] = cc.get(f['clay_body'], 0) + 1
            top = max(cc, key=cc.get) if cc else "None"
            st.metric("🏺 Top Clay Body", top.split()[0] if top != "None" else "None")
        with c4:
            st.metric("🔥 Total Firings", len(firings))

        c1, c2 = st.columns(2)
        with c1:
            if len(firings) > 1:
                data = []
                for f in firings[-10:]:
                    zo = f.get('zone_offsets') or {}
                    for z in ['top', 'middle', 'bottom']:
                        data.append({'Date': f['date'], 'Zone': z.title(), 'Offset': zo.get(z, 0)})
                fig = px.line(pd.DataFrame(data), x='Date', y='Offset', color='Zone',
                              title="Zone Offset Trends (Last 10)", markers=True)
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            tc = {}
            for f in firings:
                t = f.get('firing_type', 'unknown')
                tc[t] = tc.get(t, 0) + 1
            if tc:
                fig = px.pie(values=list(tc.values()), names=list(tc.keys()),
                             title="Firing Type Distribution")
                st.plotly_chart(fig, use_container_width=True)

# ============================================================
# PAGE: Help
# ============================================================
elif page == "❓ Help":
    st.header("❓ Help & User Guide")

    st.subheader("🚀 Quick Start Guide")
    with st.expander("1. Set Your Zone Offsets"):
        st.write("Start in the Zone Control tab. Set your initial offsets. Most kilns start around 18°F but yours may differ.")
    with st.expander("2. Log Your First Firing"):
        st.write("Use the Firing Log tab. Be specific: 'hot cone 6', 'cone 7', 'perfect cone 6'. More detail = better AI suggestions.")
    with st.expander("3. Track Your Hardware"):
        st.write("Go to Maintenance and set your element install date and current firing count.")
    with st.expander("4. Use AI Suggestions"):
        st.write("After 2–3 firings, the app suggests offset adjustments based on your actual results.")
    with st.expander("5. Analyze Your Progress"):
        st.write("Check Analytics for success rate trends, top clay bodies, and firing patterns.")

    st.subheader("🔧 Common Problems & Solutions")
    st.error("🔥 **Overfiring** (Getting Cone 7 when targeting Cone 6)")
    st.write("**Solution:** Increase your offset by 15–25°F. For severe overfiring, try 30–40°F.")
    st.info("🧊 **Underfiring** (Soft cone 6 or cone 5)")
    st.write("**Solution:** Decrease offset by 10–20°F. Check if elements are aging or thermocouples drifting.")
    st.warning("⚖️ **Uneven Firing** (Different zones firing differently)")
    st.write("**Solution:** Use individual zone offsets. Top zones often need higher offsets due to heat rise.")

# ============================================================
# PAGE: About
# ============================================================
elif page == "ℹ️ About":
    st.header("ℹ️ About KilnMaster Pro")

    st.subheader("💡 The Inspiration")
    st.info("""
    KilnMaster Pro was inspired by **Alford Wayman** at **Creek Road Pottery LLC**, who shared insights about
    the universal challenges potters face with kiln management and helped identify the need for better firing
    documentation tools.

    Though Alford works primarily with gas kilns, his observations about the pottery community's struggles
    with inconsistent firings, lost records, and maintenance tracking highlighted problems that span all kiln types.
    His humble suggestion that "maybe an app could help" sparked the creation of this comprehensive solution.
    """)

    st.subheader("🎯 The Problem We Solve")
    st.write("""
    - Kiln offset guesswork and trial-and-error
    - Lost firing records and maintenance schedules
    - Expensive element replacement surprises
    - Inconsistent firing results across zones
    - No data-driven insights for improvement
    """)

    st.subheader("✨ Our Solution")
    st.write("""
    - AI-powered offset recommendations
    - Cloud-synced firing and maintenance logs — your data follows you anywhere
    - Predictive hardware replacement alerts
    - Individual zone control and tracking
    - Advanced analytics and trend analysis
    """)

    st.subheader("🏆 Special Thanks")
    st.success("""
    **Alford Wayman** — Creek Road Pottery LLC

    The thoughtful observer who identified this need. His insights about the ceramic community's shared
    challenges with firing consistency and record-keeping helped inspire this digital solution.
    """)

    st.balloons()

# ============================================================
# Footer
# ============================================================
st.divider()
st.markdown("""
<div style="text-align:center; color:gray;">
    <p>🔥 Made with ❤️ for the Ceramic Community | KilnMaster Pro v2.0 — Cloud Edition</p>
</div>
""", unsafe_allow_html=True)
