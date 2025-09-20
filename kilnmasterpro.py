import streamlit as st
import json
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import base64

# Page config
st.set_page_config(
    page_title="KilnMaster Pro",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'firings' not in st.session_state:
    st.session_state.firings = []

if 'zone_offsets' not in st.session_state:
    st.session_state.zone_offsets = {'top': 18, 'middle': 18, 'bottom': 18}

if 'hardware' not in st.session_state:
    st.session_state.hardware = {
        'elements': {'installed': '', 'firing_count': 0, 'max_life': 300},
        'thermocouples': {'installed': '', 'firing_count': 0, 'max_life': 1000},
        'relays': {'installed': '', 'firing_count': 0, 'max_life': 500}
    }

if 'programs' not in st.session_state:
    st.session_state.programs = []

# Constants
CONE_TEMPS = {
    '04': 1830, '03': 1850, '02': 1870, '01': 1890, '1': 1910,
    '2': 1920, '3': 1930, '4': 1945, '5': 1975, '6': 1995,
    '7': 2015, '8': 2035, '9': 2055, '10': 2075
}

CLAY_BODIES = [
    'Cone 6 Stoneware', 'Porcelain', 'Buff Stoneware', 'White Stoneware', 
    'Speckled Stoneware', 'Dark Stoneware', 'Earthenware', 'Custom Mix'
]

# Helper functions
def calculate_suggested_offsets():
    """Calculate AI-suggested offsets based on recent firing history"""
    if len(st.session_state.firings) == 0:
        return None
    
    recent_firings = st.session_state.firings[-5:]  # Last 5 firings
    suggestions = {'top': 0, 'middle': 0, 'bottom': 0}
    
    for zone in ['top', 'middle', 'bottom']:
        total_adjustment = 0
        valid_firings = 0
        
        for firing in recent_firings:
            result = firing.get('zone_results', {}).get(zone, firing.get('actual_result', '')).lower()
            target = int(firing.get('target_cone', 6))
            
            if 'cone' in result:
                if 'hot' in result or 'soft' in result:
                    total_adjustment += 12
                    valid_firings += 1
                elif 'perfect' in result or 'good' in result:
                    total_adjustment += 0
                    valid_firings += 1
                else:
                    # Try to extract cone number
                    import re
                    cone_match = re.search(r'cone\s*(\d+)', result)
                    if cone_match:
                        actual_cone = int(cone_match.group(1))
                        if actual_cone > target:
                            total_adjustment += (actual_cone - target) * 18
                            valid_firings += 1
                        elif actual_cone < target:
                            total_adjustment -= (target - actual_cone) * 18
                            valid_firings += 1
        
        if valid_firings > 0:
            adjustment = round(total_adjustment / valid_firings)
            current_offset = st.session_state.zone_offsets[zone]
            suggestions[zone] = max(0, min(100, current_offset + adjustment))
        else:
            suggestions[zone] = st.session_state.zone_offsets[zone]
    
    return suggestions

def get_health_status(component_data):
    """Get health status for hardware components"""
    usage = (component_data['firing_count'] / component_data['max_life']) * 100
    if usage < 60:
        return {'color': 'green', 'status': 'Excellent', 'emoji': '✅'}
    elif usage < 85:
        return {'color': 'orange', 'status': 'Monitor', 'emoji': '⚠️'}
    else:
        return {'color': 'red', 'status': 'Replace Soon', 'emoji': '🚨'}

def export_data():
    """Export all data as JSON"""
    data = {
        'firings': st.session_state.firings,
        'zone_offsets': st.session_state.zone_offsets,
        'hardware': st.session_state.hardware,
        'programs': st.session_state.programs,
        'exported': datetime.now().isoformat()
    }
    return json.dumps(data, indent=2)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #f97316, #dc2626);
        padding: 2rem;
        border-radius: 1rem;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #f97316;
    }
    .zone-card {
        background: linear-gradient(135deg, #3b82f6, #1d4ed8);
        color: white;
        padding: 1.5rem;
        border-radius: 1rem;
        margin: 0.5rem 0;
    }
    .success-rate {
        font-size: 2rem;
        font-weight: bold;
        color: #059669;
    }
    .firing-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🔥 KilnMaster Pro</h1>
    <p>Advanced Kiln Management & Analytics</p>
</div>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("🧭 Navigation")
page = st.sidebar.selectbox(
    "Choose a section:",
    ["🔥 Firing Log", "🎯 Zone Control", "⚙️ Programs", "🔧 Maintenance", "📊 Analytics", "❓ Help", "ℹ️ About"]
)

# Export button in sidebar
if st.sidebar.button("📥 Export Data"):
    data_json = export_data()
    b64 = base64.b64encode(data_json.encode()).decode()
    href = f'<a href="data:application/json;base64,{b64}" download="kiln_data_{datetime.now().strftime("%Y%m%d")}.json">Download Kiln Data</a>'
    st.sidebar.markdown(href, unsafe_allow_html=True)

# Main content based on selected page
if page == "🔥 Firing Log":
    st.header("🔥 Firing Log")
    
    # Dashboard metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🎯 Zone Offsets",
            value=f"T:{st.session_state.zone_offsets['top']}° M:{st.session_state.zone_offsets['middle']}° B:{st.session_state.zone_offsets['bottom']}°"
        )
    
    with col2:
        st.metric(
            label="📈 Total Firings",
            value=len(st.session_state.firings)
        )
    
    with col3:
        elements = st.session_state.hardware['elements']
        usage = round((elements['firing_count'] / elements['max_life']) * 100)
        st.metric(
            label="⚡ Element Health",
            value=f"{usage}%",
            delta=f"{elements['firing_count']}/{elements['max_life']} firings"
        )
    
    with col4:
        if st.session_state.firings:
            success_count = sum(1 for f in st.session_state.firings 
                              if any(word in f.get('actual_result', '').lower() 
                                   for word in ['perfect', 'good']) or
                                 (f'cone {f.get("target_cone", "")}' in f.get('actual_result', '').lower() and 
                                  'hot' not in f.get('actual_result', '').lower()))
            success_rate = round((success_count / len(st.session_state.firings)) * 100)
        else:
            success_rate = 0
        st.metric(
            label="🎯 Success Rate",
            value=f"{success_rate}%"
        )
    
    # Smart suggestions
    suggestions = calculate_suggested_offsets()
    if suggestions and any(suggestions[zone] != st.session_state.zone_offsets[zone] for zone in suggestions):
        st.info("🤖 **AI Suggestions Available!** Based on your recent firings:")
        col1, col2, col3 = st.columns(3)
        for i, zone in enumerate(['top', 'middle', 'bottom']):
            with [col1, col2, col3][i]:
                if suggestions[zone] != st.session_state.zone_offsets[zone]:
                    st.write(f"**{zone.title()} Zone:** {suggestions[zone]}°F")
                    if st.button(f"Apply {zone.title()}", key=f"apply_{zone}"):
                        st.session_state.zone_offsets[zone] = suggestions[zone]
                        st.success(f"Applied {zone} zone suggestion!")
                        st.experimental_rerun()
    
    # Add new firing form
    st.subheader("➕ Log New Firing")
    
    with st.form("new_firing"):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            target_cone = st.selectbox("Target Cone", list(CONE_TEMPS.keys()), index=5)
        
        with col2:
            firing_type = st.selectbox("Firing Type", ["bisque", "glaze", "test"], index=1)
        
        with col3:
            clay_body = st.selectbox("Clay Body", [""] + CLAY_BODIES)
        
        with col4:
            load_density = st.selectbox("Load Density", ["full", "partial", "test"])
        
        col1, col2 = st.columns(2)
        
        with col1:
            actual_result = st.text_input("Overall Result", placeholder="e.g., 'hot cone 6', 'cone 7', 'perfect cone 6'")
        
        with col2:
            glaze_type = st.text_input("Glaze Type (optional)", placeholder="e.g., 'Clear', 'Celadon', 'Matte Black'")
        
        # Zone-specific results
        st.write("**Zone-Specific Results (optional):**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            top_result = st.text_input("Top Zone Result", placeholder="Optional")
        
        with col2:
            middle_result = st.text_input("Middle Zone Result", placeholder="Optional")
        
        with col3:
            bottom_result = st.text_input("Bottom Zone Result", placeholder="Optional")
        
        notes = st.text_area("Notes", placeholder="Any observations about the firing...")
        
        submitted = st.form_submit_button("🔥 Log Firing")
        
        if submitted and actual_result:
            new_firing = {
                'id': len(st.session_state.firings) + 1,
                'date': datetime.now().strftime("%Y-%m-%d"),
                'time': datetime.now().strftime("%H:%M:%S"),
                'zone_offsets': st.session_state.zone_offsets.copy(),
                'target_cone': target_cone,
                'actual_result': actual_result,
                'zone_results': {
                    'top': top_result,
                    'middle': middle_result,
                    'bottom': bottom_result
                },
                'firing_type': firing_type,
                'clay_body': clay_body,
                'glaze_type': glaze_type,
                'load_density': load_density,
                'notes': notes,
                'timestamp': datetime.now().isoformat()
            }
            
            st.session_state.firings.append(new_firing)
            
            # Update hardware firing counts
            for component in st.session_state.hardware:
                st.session_state.hardware[component]['firing_count'] += 1
            
            st.success("✅ Firing logged successfully!")
            st.experimental_rerun()
    
    # Recent firings display
    st.subheader("📋 Recent Firings")
    
    if st.session_state.firings:
        for firing in reversed(st.session_state.firings[-10:]):  # Show last 10 firings
            with st.expander(f"{firing['date']} - {firing['firing_type'].title()} - Cone {firing['target_cone']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Result:** {firing['actual_result']}")
                    st.write(f"**Target:** Cone {firing['target_cone']}")
                    if firing['clay_body']:
                        st.write(f"**Clay Body:** {firing['clay_body']}")
                    if firing['glaze_type']:
                        st.write(f"**Glaze:** {firing['glaze_type']}")
                
                with col2:
                    offsets = firing['zone_offsets']
                    st.write(f"**Zone Offsets:** T:{offsets['top']}° M:{offsets['middle']}° B:{offsets['bottom']}°")
                    st.write(f"**Load:** {firing['load_density'].title()}")
                    st.write(f"**Time:** {firing['time']}")
                
                zone_results = firing['zone_results']
                if any(zone_results.values()):
                    st.write("**Zone Results:**")
                    for zone, result in zone_results.items():
                        if result:
                            st.write(f"- {zone.title()}: {result}")
                
                if firing['notes']:
                    st.write(f"**Notes:** {firing['notes']}")
    else:
        st.info("🔥 No firings logged yet. Start by logging your first firing above!")

elif page == "🎯 Zone Control":
    st.header("🎯 Zone Control Center")
    st.write("Manage individual zone offsets for precise firing control")
    
    # Zone offset controls
    col1, col2, col3 = st.columns(3)
    
    zones = ['top', 'middle', 'bottom']
    colors = ['🔴', '🔵', '🟢']
    
    for i, zone in enumerate(zones):
        with [col1, col2, col3][i]:
            st.markdown(f"""
            <div class="zone-card">
                <h3>{colors[i]} {zone.title()} Zone</h3>
                <div style="font-size: 2rem; font-weight: bold;">{st.session_state.zone_offsets[zone]}°F</div>
            </div>
            """, unsafe_allow_html=True)
            
            new_offset = st.number_input(
                f"{zone.title()} Zone Offset (°F)",
                min_value=0,
                max_value=100,
                value=st.session_state.zone_offsets[zone],
                key=f"offset_{zone}"
            )
            
            if new_offset != st.session_state.zone_offsets[zone]:
                st.session_state.zone_offsets[zone] = new_offset
                st.success(f"✅ {zone.title()} zone updated!")
    
    # Zone performance chart
    if st.session_state.firings:
        st.subheader("📊 Recent Zone Performance")
        
        recent_firings = st.session_state.firings[-5:]
        
        data = []
        for firing in recent_firings:
            date = firing['date']
            offsets = firing['zone_offsets']
            for zone in ['top', 'middle', 'bottom']:
                data.append({
                    'Date': date,
                    'Zone': zone.title(),
                    'Offset': offsets[zone],
                    'Target Cone': f"Cone {firing['target_cone']}",
                    'Result': firing['actual_result']
                })
        
        if data:
            df = pd.DataFrame(data)
            fig = px.line(df, x='Date', y='Offset', color='Zone', 
                         title="Zone Offset Trends",
                         markers=True)
            st.plotly_chart(fig, use_container_width=True)

elif page == "⚙️ Programs":
    st.header("⚙️ Firing Programs")
    st.write("Create and manage custom firing schedules")
    
    # Add new program
    st.subheader("➕ Create New Program")
    
    with st.form("new_program"):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            program_name = st.text_input("Program Name", placeholder="e.g., Cone 6 Slow Glaze")
        
        with col2:
            program_type = st.selectbox("Type", ["bisque", "glaze", "test"])
        
        with col3:
            target_temp = st.number_input("Target Temp (°F)", value=2165)
        
        with col4:
            ramp_rate = st.number_input("Ramp Rate (°F/hr)", value=150)
        
        col1, col2 = st.columns(2)
        
        with col1:
            hold_time = st.number_input("Hold Time (min)", value=10)
        
        with col2:
            recommended_clay = st.selectbox("Recommended Clay", [""] + CLAY_BODIES)
        
        program_notes = st.text_area("Program Notes", placeholder="Special instructions or notes...")
        
        submitted = st.form_submit_button("💾 Save Program")
        
        if submitted and program_name:
            new_program = {
                'id': len(st.session_state.programs) + 1,
                'name': program_name,
                'type': program_type,
                'target_temp': target_temp,
                'ramp_rate': ramp_rate,
                'hold_time': hold_time,
                'clay_body': recommended_clay,
                'notes': program_notes,
                'created': datetime.now().strftime("%Y-%m-%d")
            }
            
            st.session_state.programs.append(new_program)
            st.success("✅ Program saved successfully!")
            st.experimental_rerun()
    
    # Display saved programs
    st.subheader("📚 Saved Programs")
    
    if st.session_state.programs:
        for program in st.session_state.programs:
            with st.expander(f"{program['name']} ({program['type'].title()})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Target:** {program['target_temp']}°F")
                    st.write(f"**Ramp Rate:** {program['ramp_rate']}°F/hr")
                    st.write(f"**Hold Time:** {program['hold_time']} min")
                
                with col2:
                    st.write(f"**Type:** {program['type'].title()}")
                    st.write(f"**Created:** {program['created']}")
                    if program['clay_body']:
                        st.write(f"**Recommended Clay:** {program['clay_body']}")
                
                if program['notes']:
                    st.write(f"**Notes:** {program['notes']}")
    else:
        st.info("📚 No programs saved yet. Create your first firing program above!")

elif page == "🔧 Maintenance":
    st.header("🔧 Hardware Maintenance")
    st.write("Monitor and maintain your kiln components")
    
    # Hardware status cards
    components = ['elements', 'thermocouples', 'relays']
    component_names = ['Elements', 'Thermocouples', 'Relays']
    
    for i, component in enumerate(components):
        data = st.session_state.hardware[component]
        health = get_health_status(data)
        usage_percent = round((data['firing_count'] / data['max_life']) * 100)
        
        st.subheader(f"{health['emoji']} {component_names[i]}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            new_install_date = st.date_input(
                f"{component_names[i]} Install Date",
                value=date.today() if not data['installed'] else datetime.fromisoformat(data['installed']).date(),
                key=f"install_{component}"
            )
            st.session_state.hardware[component]['installed'] = new_install_date.isoformat()
        
        with col2:
            new_firing_count = st.number_input(
                f"{component_names[i]} Firing Count",
                min_value=0,
                value=data['firing_count'],
                key=f"count_{component}"
            )
            st.session_state.hardware[component]['firing_count'] = new_firing_count
        
        with col3:
            new_max_life = st.number_input(
                f"{component_names[i]} Expected Life",
                min_value=1,
                value=data['max_life'],
                key=f"life_{component}"
            )
            st.session_state.hardware[component]['max_life'] = new_max_life
        
        # Progress bar and status
        progress_color = health['color']
        st.write(f"**Usage:** {usage_percent}% - {health['status']}")
        st.progress(min(usage_percent / 100, 1.0))
        
        if usage_percent >= 85:
            st.error(f"🚨 {component_names[i]} replacement recommended soon! ({usage_percent}% used)")
        elif usage_percent >= 60:
            st.warning(f"⚠️ Monitor {component_names[i]} closely. ({usage_percent}% used)")
        else:
            st.success(f"✅ {component_names[i]} in excellent condition. ({usage_percent}% used)")
        
        st.divider()

elif page == "📊 Analytics":
    st.header("📊 Firing Analytics")
    st.write("Insights and trends from your firing data")
    
    if not st.session_state.firings:
        st.info("📊 No data available yet. Log some firings to see detailed analytics!")
    else:
        firings = st.session_state.firings
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            success_count = sum(1 for f in firings 
                              if any(word in f.get('actual_result', '').lower() 
                                   for word in ['perfect', 'good']))
            success_rate = round((success_count / len(firings)) * 100)
            st.metric("🎯 Success Rate", f"{success_rate}%")
        
        with col2:
            avg_offset = round(sum(f['zone_offsets']['middle'] for f in firings) / len(firings))
            st.metric("🌡️ Avg Middle Offset", f"{avg_offset}°F")
        
        with col3:
            clay_counts = {}
            for f in firings:
                if f.get('clay_body'):
                    clay_counts[f['clay_body']] = clay_counts.get(f['clay_body'], 0) + 1
            top_clay = max(clay_counts.keys(), key=lambda k: clay_counts[k]) if clay_counts else "None"
            st.metric("🏺 Top Clay Body", top_clay.split()[0] if top_clay != "None" else "None")
        
        with col4:
            st.metric("🔥 Total Firings", len(firings))
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Zone offset trends
            if len(firings) > 1:
                recent_firings = firings[-10:]
                
                data = []
                for firing in recent_firings:
                    date = firing['date']
                    offsets = firing['zone_offsets']
                    for zone in ['top', 'middle', 'bottom']:
                        data.append({
                            'Date': date,
                            'Zone': zone.title(),
                            'Offset': offsets[zone]
                        })
                
                if data:
                    df = pd.DataFrame(data)
                    fig = px.line(df, x='Date', y='Offset', color='Zone', 
                                 title="Zone Offset Trends (Last 10 Firings)")
                    st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Firing type distribution
            type_counts = {}
            for f in firings:
                ftype = f.get('firing_type', 'unknown')
                type_counts[ftype] = type_counts.get(ftype, 0) + 1
            
            if type_counts:
                fig = px.pie(values=list(type_counts.values()), 
                           names=list(type_counts.keys()),
                           title="Firing Type Distribution")
                st.plotly_chart(fig, use_container_width=True)

elif page == "❓ Help":
    st.header("❓ Help & User Guide")
    st.write("Learn how to master your kiln firing with KilnMaster Pro")
    
    # Quick Start Guide
    st.subheader("🚀 Quick Start Guide")
    
    with st.expander("1. Set Your Zone Offsets"):
        st.write("""
        Start in the Zone Control tab. Set your initial offsets based on your kiln's current performance. 
        Most kilns start around 18°F but yours may be different.
        """)
    
    with st.expander("2. Log Your First Firing"):
        st.write("""
        Use the Firing Log tab to record your firing results. Be specific: "hot cone 6", "cone 7", "perfect cone 6", etc. 
        The more detail, the better the AI suggestions.
        """)
    
    with st.expander("3. Track Your Hardware"):
        st.write("""
        Go to Maintenance tab and set your element install date and current firing count. 
        This helps predict when replacements are needed.
        """)
    
    with st.expander("4. Use AI Suggestions"):
        st.write("""
        After 2-3 firings, the app will suggest offset adjustments. 
        These are based on your actual results and kiln behavior patterns.
        """)
    
    with st.expander("5. Analyze Your Progress"):
        st.write("""
        Check the Analytics tab to see your success rate trends, most-used clay bodies, and firing patterns over time.
        """)
    
    # Troubleshooting
    st.subheader("🔧 Common Problems & Solutions")
    
    st.error("🔥 **Overfiring** (Getting Cone 7 when targeting Cone 6)")
    st.write("**Solution:** Increase your offset by 15-25°F. For severe overfiring (cone 8+), try 30-40°F increase.")
    
    st.info("🧊 **Underfiring** (Getting soft cone 6 or cone 5)")
    st.write("**Solution:** Decrease your offset by 10-20°F. Check if your elements are aging or thermocouples drifting.")
    
    st.warning("⚖️ **Uneven Firing** (Different zones firing differently)")
    st.write("**Solution:** Use individual zone offsets. Top zones often need higher offsets due to heat rise.")

elif page == "ℹ️ About":
    st.header("ℹ️ About KilnMaster Pro")
    st.write("The story behind the world's most advanced kiln management system")
    
    st.subheader("💡 The Inspiration")
    st.info("""
    KilnMaster Pro was inspired by **Alford Wayman** at **Creek Road Pottery LLC**, who shared insights about 
    the universal challenges potters face with kiln management and helped identify the need for better firing 
    documentation tools.
    
    Though Alford works primarily with gas kilns, his observations about the pottery community's struggles with 
    inconsistent firings, lost records, and maintenance tracking highlighted problems that span all kiln types. 
    His humble suggestion that "maybe an app could help" sparked the creation of this comprehensive solution for 
    electric kiln management.
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
    - Comprehensive firing and maintenance logs
    - Predictive hardware replacement alerts
    - Individual zone control and tracking
    - Advanced analytics and trend analysis
    """)
    
    st.subheader("🏆 Special Thanks")
    st.success("""
    **Alford Wayman** - Creek Road Pottery LLC
    
    The thoughtful observer who identified this need. Although Alford works with gas kilns rather than electric, 
    his insights about the ceramic community's shared challenges with firing consistency and record-keeping helped 
    inspire this digital solution. His humble suggestion to explore technology solutions opened the door to helping 
    electric kiln users worldwide.
    """)
    
    st.balloons()  # Celebratory balloons for the about page!

# Footer
st.divider()
st.markdown("""
<div style="text-align: center; color: gray;">
    <p>🔥 Made with ❤️ for the Ceramic Community | KilnMaster Pro v1.0</p>
</div>
""", unsafe_allow_html=True)
