"""Streamlit app for qualitative coding of poems from Poets.org."""

import os
import time
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import numpy as np

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import CodingRecord
from scraper import fetch_html, parse_poem
from storage import save_record, latest_record_for_coder, get_coding_stats
from utils import sha1, normalize_tags


# Page configuration
st.set_page_config(
    page_title="Poem Qualitative Coding",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)
# GLOBAL CONFIGURATION - UI CUSTOMIZATION SETTINGS

ENABLE_UI_CUSTOMIZATION = True  # Set to False to disable all UI customization
ENABLE_TAG_COLUMNS_SETTING = True  # Set to False to disable tag columns setting
ENABLE_TAG_FONT_SIZE_SETTING = True  # Set to False to disable font size setting
ENABLE_TIMING_METHOD_SETTING = True  # Set to False to disable timing method selection
ENABLE_GRID_DENSITY_SETTING = True  # Set to False to disable grid density setting

DEFAULT_TAG_COLUMNS = 4  # Default number of columns for tag display
DEFAULT_TAG_FONT_SIZE = "medium"  # Default font size: "small", "medium", "large"
DEFAULT_TIMING_METHOD = "once"  # Default timing method: "invisible" or "staged"
DEFAULT_GRID_DENSITY = "1.0"  # Default grid density: "1.0", "0.5", "0.1"

# Font size mappings
FONT_SIZE_MAPPING = {
    "small": "0.8rem",
    "medium": "1rem", 
    "large": "1.2rem"
}

# Grid density mappings (number of points per axis)
GRID_DENSITY_MAPPING = {
    "1.0": 21,      # 21x21 = 441 points, precision to 1.0
    "0.5": 41,      # 41x41 = 1681 points, precision to 0.5
    "0.1": 201      # 201x201 = 40401 points, precision to 0.1
}

# Global CSS for tag styling
st.markdown("""
<style>
/* Global checkbox label styling */
.stCheckbox label {
    font-size: 1rem !important;
}

.stCheckbox label div {
    font-size: 1rem !important;
}

.stCheckbox label div p {
    font-size: 1rem !important;
    margin: 0.2rem 0 !important;
}

.stCheckbox {
    margin: 0.1rem 0 !important;
}

/* Additional targeting for different Streamlit versions */
div[data-testid="stCheckbox"] label {
    font-size: 1rem !important;
}

div[data-testid="stCheckbox"] label div {
    font-size: 1rem !important;
}

div[data-testid="stCheckbox"] label div p {
    font-size: 1rem !important;
}
</style>
""", unsafe_allow_html=True)

TOP_20_TAGS = [
    'nature', 'body', 'death', 'love', 'existential', 'identity', 'self',
    'beauty', 'america', 'loss', 'animals', 'history', 'memories', 'family',
    'writing', 'ancestry', 'thought', 'landscapes', 'war', 'time'
]

TOP_50_TAGS = TOP_20_TAGS + [
    'religion', 'grief', 'violence', 'aging', 'childhood', 'desire', 'night', 'mothers',
    'language', 'birds', 'social justice', 'music', 'flowers', 'politics',
    'hope', 'heartache', 'fathers', 'gender', 'environment', 'spirituality',
    'loneliness', 'oceans', 'dreams', 'survival', 'cities', 'earth', 'despair',
    'anxiety', 'weather', 'illness'
]

ALL_CORPUS_TAGS = TOP_50_TAGS + [
    'past', 'myth', 'travel', 'sadness', 'lgbtq', 'mourning', 'work', 'future', 
    'plants', 'afterlife', 'happiness', 'romance', 'sex', 'eating', 'love, contemporary', 
    'beginning', 'creation', 'turmoil', 'friendship', 'parenting', 'pastoral',
    'lust', 'immigration', 'daughters', 'anger', 'nostalgia', 'ambition',
    'migration', 'space', 'carpe diem', 'ghosts', 'marriage', 'reading',
    'popular culture', 'economy', 'tragedy', 'drinking', 'clothing', 'sons',
    'gun violence', 'americana', 'buildings', 'money', 'silence', 'gardens',
    'rebellion', 'new york city', 'heroes', 'science', 'gratitude',
    'storms', 'deception', 'technology', 'slavery', 'cooking', 'apocalypse',
    'humor', 'dance', 'doubt', 'regret', 'flight', 'sports',
    'national parks', 'school', 'oblivion', 'dogs', 'suffrage',
    'old age', 'drugs', 'teaching', 'innocence', 'sisters', 'enemies', 'brothers',
    'covid-19', 'math', 'american revolution', 'incarceration', 'pets', 'underworld',
    'pacifism', 'divorce', 'suburbia', 'theft', 'patience', 'movies', 'civil war',
    'cats', 'moving', 'luck', 'miracles', 'jealousy', 'vanity', 'infidelity', 'high school'
]

DEFAULT_BASE_TAGS = TOP_20_TAGS

MOOD_OPTIONS = ["anger", "anticipation", "disgust", "fear", "joy", "sadness", "surprise", "trust"]
SENTIMENT_OPTIONS = ["positive", "neutral", "negative", "unsure"]


def get_last_completed_index_for_coder(coder_id):
    """Get the index of the last completed poem for a specific coder."""
    if not coder_id.strip():
        return 0
        
    try:
        coding_dir = Path("coding_records")
        if not coding_dir.exists():
            return 0
            
        jsonl_path = coding_dir / "codings.jsonl"
        if not jsonl_path.exists():
            return 0
        
        completed_urls = set()
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        if (record.get('coder_id') == coder_id.strip() and 
                            record.get('is_complete', False)):
                            completed_urls.add(record.get('url'))
                    except json.JSONDecodeError:
                        continue
        
        return len(completed_urls)
    except Exception:
        return 0


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if 'coder_id' not in st.session_state:
        st.session_state.coder_id = ""
    if 'base_tags' not in st.session_state:
        st.session_state.base_tags = DEFAULT_BASE_TAGS.copy()
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    if 'poems_df' not in st.session_state:
        st.session_state.poems_df = None
    if 'current_poem_meta' not in st.session_state:
        st.session_state.current_poem_meta = None
    if 'current_poem_text' not in st.session_state:
        st.session_state.current_poem_text = None
    if 'extraction_error' not in st.session_state:
        st.session_state.extraction_error = None
    if 'sentiment_x' not in st.session_state:
        st.session_state.sentiment_x = 0.0
    if 'sentiment_y' not in st.session_state:
        st.session_state.sentiment_y = 0.0
    if 'tag_set_preference' not in st.session_state:
        st.session_state.tag_set_preference = "top20"
    if 'just_saved_and_reset' not in st.session_state:
        st.session_state.just_saved_and_reset = False
    # Timer functionality
    if 'timer_start_time' not in st.session_state:
        st.session_state.timer_start_time = None
    if 'current_poem_url' not in st.session_state:
        st.session_state.current_poem_url = None
    # Staged timing functionality
    if 'timing_method' not in st.session_state:
        st.session_state.timing_method = DEFAULT_TIMING_METHOD
    if 'current_stage' not in st.session_state:
        st.session_state.current_stage = "poem"  # "poem", "themes", "mood", "chart", "notes"
    if 'stage_start_time' not in st.session_state:
        st.session_state.stage_start_time = None
    if 'stage_timings' not in st.session_state:
        st.session_state.stage_timings = {}
    # UI customization (use global defaults)
    if 'tag_columns' not in st.session_state:
        st.session_state.tag_columns = DEFAULT_TAG_COLUMNS
    if 'tag_font_size' not in st.session_state:
        st.session_state.tag_font_size = DEFAULT_TAG_FONT_SIZE
    if 'grid_density' not in st.session_state:
        st.session_state.grid_density = DEFAULT_GRID_DENSITY


def load_poets_csv(file_path: str) -> Optional[pd.DataFrame]:
    """Load and validate poets CSV file."""
    try:
        if not os.path.exists(file_path):
            st.error(f"File not found: {file_path}")
            return None
        
        df = pd.read_csv(file_path)
        
        required_columns = ['title', 'author', 'url']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            st.error(f"Missing required columns: {', '.join(missing_columns)}")
            st.error(f"Found columns: {', '.join(df.columns.tolist())}")
            return None
        
        df = df.dropna(subset=['url'])
        df = df[df['url'].str.strip() != '']
        df = df.drop_duplicates(subset=['url'])
        df = df.reset_index(drop=True)
        
        if len(df) == 0:
            st.error("No valid URLs found in the CSV file.")
            return None
        
        return df
        
    except Exception as e:
        st.error(f"Error loading CSV: {str(e)}")
        return None


def start_timer():
    """Start the timer for the current poem."""
    st.session_state.timer_start_time = time.time()

def stop_timer():
    """Stop the timer and return the elapsed time in seconds."""
    if st.session_state.timer_start_time is not None:
        elapsed = time.time() - st.session_state.timer_start_time
        st.session_state.timer_start_time = None
        return elapsed
    return 0.0

def get_elapsed_time():
    """Get the current elapsed time without stopping the timer."""
    if st.session_state.timer_start_time is not None:
        return time.time() - st.session_state.timer_start_time
    return 0.0

def start_stage_timer(stage_name):
    """Start timing for a specific stage."""
    st.session_state.stage_start_time = time.time()
    st.session_state.current_stage = stage_name

def stop_stage_timer():
    """Stop the current stage timer and record the time."""
    if st.session_state.stage_start_time is not None and st.session_state.current_stage:
        elapsed = time.time() - st.session_state.stage_start_time
        st.session_state.stage_timings[st.session_state.current_stage] = elapsed
        st.session_state.stage_start_time = None
        return elapsed
    return 0.0

def get_stage_elapsed_time():
    """Get the current stage elapsed time without stopping the timer."""
    if st.session_state.stage_start_time is not None:
        return time.time() - st.session_state.stage_start_time
    return 0.0

def reset_stage_timings():
    """Reset all stage timings."""
    st.session_state.stage_timings = {}
    st.session_state.current_stage = "poem"
    st.session_state.stage_start_time = None

def apply_tag_style():
    """Apply custom tag styling based on user preferences."""
    # Use global font size mapping
    font_size = FONT_SIZE_MAPPING.get(st.session_state.tag_font_size, "1rem")
    
    # Apply dynamic CSS for checkbox labels using JavaScript
    st.markdown(f"""
    <script>
    // Function to apply font size to all checkboxes
    function applyCheckboxFontSize() {{
        const checkboxes = document.querySelectorAll('.stCheckbox label, div[data-testid="stCheckbox"] label');
        checkboxes.forEach(checkbox => {{
            checkbox.style.fontSize = '{font_size}';
            const divs = checkbox.querySelectorAll('div');
            divs.forEach(div => {{
                div.style.fontSize = '{font_size}';
                const ps = div.querySelectorAll('p');
                ps.forEach(p => {{
                    p.style.fontSize = '{font_size}';
                }});
            }});
        }});
    }}
    
    // Apply immediately
    applyCheckboxFontSize();
    
    // Apply after a short delay to catch dynamically loaded elements
    setTimeout(applyCheckboxFontSize, 100);
    setTimeout(applyCheckboxFontSize, 500);
    </script>
    """, unsafe_allow_html=True)
    
    # Also apply CSS as backup
    st.markdown(f"""
    <style>
    .stCheckbox label {{
        font-size: {font_size} !important;
    }}
    
    .stCheckbox label div {{
        font-size: {font_size} !important;
    }}
    
    .stCheckbox label div p {{
        font-size: {font_size} !important;
    }}
    
    div[data-testid="stCheckbox"] label {{
        font-size: {font_size} !important;
    }}
    
    div[data-testid="stCheckbox"] label div {{
        font-size: {font_size} !important;
    }}
    
    div[data-testid="stCheckbox"] label div p {{
        font-size: {font_size} !important;
    }}
    </style>
    """, unsafe_allow_html=True)

def fetch_and_parse_current_poem():
    """Fetch and parse the current poem."""
    if st.session_state.poems_df is None or len(st.session_state.poems_df) == 0:
        return
    
    current_url = st.session_state.poems_df.iloc[st.session_state.current_index]['url']
    
    # Start timer if this is a new poem
    if st.session_state.current_poem_url != current_url:
        if st.session_state.timing_method == "once":
            start_timer()
        elif st.session_state.timing_method == "staged":
            reset_stage_timings()
            start_stage_timer("poem")
        st.session_state.current_poem_url = current_url
    
    try:
        with st.spinner("Fetching poem..."):
            html = fetch_html(current_url)
            meta, text = parse_poem(html, current_url)
            
            st.session_state.current_poem_meta = meta
            st.session_state.current_poem_text = text
            st.session_state.extraction_error = None
            
    except Exception as e:
        st.session_state.current_poem_meta = None
        st.session_state.current_poem_text = None
        st.session_state.extraction_error = str(e)


def render_sidebar():
    """Render the sidebar with controls and progress."""
    st.sidebar.title("📝 Poem Coding")
    
    previous_coder_id = st.session_state.coder_id
    st.session_state.coder_id = st.sidebar.text_input(
        "Coder ID", 
        value=st.session_state.coder_id
    )
    
    # Timing method selection (only show if enabled)
    if st.session_state.coder_id.strip():
        if ENABLE_TIMING_METHOD_SETTING:
            st.sidebar.subheader("⏱️ Timing Method")
            timing_method = st.sidebar.radio(
                "Choose timing method:",
                options=["once", "staged"],
                format_func=lambda x: "Count once at start" if x == "once" else "Count on each stage",
                index=0 if st.session_state.timing_method == "once" else 1,
                key="timing_method_radio"
            )
            
            if timing_method != st.session_state.timing_method:
                st.session_state.timing_method = timing_method
                if timing_method == "staged":
                    reset_stage_timings()
                    start_stage_timer("poem")
                st.rerun()
        else:
            # Use default value when setting is disabled
            st.session_state.timing_method = DEFAULT_TIMING_METHOD
    
    # Only load data if coder ID is entered
    if st.session_state.coder_id.strip():
        csv_path = "src/poets.csv"
        if os.path.exists(csv_path):
            if st.session_state.poems_df is None:
                df_to_load = load_poets_csv(csv_path)
                if df_to_load is not None:
                    st.session_state.poems_df = df_to_load
                    st.session_state.current_index = 0
                    fetch_and_parse_current_poem()
        else:
            st.sidebar.error("poets.csv file not found")
        
        if (st.session_state.coder_id != previous_coder_id and 
            st.session_state.coder_id.strip() != ""):
            new_index = get_last_completed_index_for_coder(st.session_state.coder_id)
            if new_index != st.session_state.current_index:
                st.session_state.current_index = new_index
                fetch_and_parse_current_poem()
                st.rerun()
        
        # UI Customization (only show if enabled)
        if ENABLE_UI_CUSTOMIZATION:
            st.sidebar.subheader("🎨 UI Settings")
            
            if ENABLE_TAG_COLUMNS_SETTING:
                tag_columns = st.sidebar.selectbox(
                    "Tag Columns",
                    options=[2, 3, 4, 5, 6],
                    index=[2, 3, 4, 5, 6].index(st.session_state.tag_columns),
                    help="Number of columns for tag display (affects spacing)"
                )
                if tag_columns != st.session_state.tag_columns:
                    st.session_state.tag_columns = tag_columns
                    st.rerun()
            else:
                # Use default value when setting is disabled
                st.session_state.tag_columns = DEFAULT_TAG_COLUMNS
            
            if ENABLE_TAG_FONT_SIZE_SETTING:
                tag_font_size = st.sidebar.selectbox(
                    "Tag Font Size",
                    options=["small", "medium", "large"],
                    index=["small", "medium", "large"].index(st.session_state.tag_font_size),
                    help="Font size for tag checkboxes"
                )
                if tag_font_size != st.session_state.tag_font_size:
                    st.session_state.tag_font_size = tag_font_size
                    st.rerun()
            else:
                # Use default value when setting is disabled
                st.session_state.tag_font_size = DEFAULT_TAG_FONT_SIZE
            
            if ENABLE_GRID_DENSITY_SETTING:
                # Handle migration from old values to new values
                current_density = st.session_state.grid_density
                if current_density not in ["1.0", "0.5", "0.1"]:
                    # Map old values to new values
                    if current_density in ["low", "medium"]:
                        st.session_state.grid_density = "1.0"
                    elif current_density == "high":
                        st.session_state.grid_density = "0.5"
                    else:
                        st.session_state.grid_density = DEFAULT_GRID_DENSITY
                
                grid_density = st.sidebar.selectbox(
                    "Chart Precision",
                    options=["1.0", "0.5", "0.1"],
                    index=["1.0", "0.5", "0.1"].index(st.session_state.grid_density),
                    format_func=lambda x: f"Precision {x} (21×21 grid)" if x == "1.0" 
                                        else f"Precision {x} (41×41 grid)" if x == "0.5"
                                        else f"Precision {x} (201×201 grid)",
                    help="Click precision on the sentiment chart. Higher precision = more clickable points but slower performance."
                )
                if grid_density != st.session_state.grid_density:
                    st.session_state.grid_density = grid_density
                    st.rerun()
            else:
                # Use default value when setting is disabled
                st.session_state.grid_density = DEFAULT_GRID_DENSITY
        
        # Show progress only if coder ID is entered and data is loaded
        if st.session_state.poems_df is not None:
            st.sidebar.subheader("📊 Progress")
            total_poems = len(st.session_state.poems_df)
            current_pos = st.session_state.current_index + 1
            
            stats = get_coding_stats()
            
            st.sidebar.metric("Current Position", f"{current_pos} / {total_poems}")
            st.sidebar.metric("Completed", stats['completed_records'])
            
            progress = current_pos / total_poems
            st.sidebar.progress(progress)


def render_sentiment_2d():
    """Render interactive 2D coordinate chart using Plotly."""
    st.subheader("Sentiment Coordinates")
    
    current_x = st.session_state.get('sentiment_x', 0.0)
    current_y = st.session_state.get('sentiment_y', 0.0)
    
    st.write("**Double click anywhere on the chart to set coordinates:**")
    
    dpi = 200

    def cm_to_pixels(cm, dpi):
        return int(cm / 2.54 * dpi)

    pixels_5cm = cm_to_pixels(5, dpi)

    def create_chart():
        fig = go.Figure()
        
        # Get grid density from session state
        grid_density = st.session_state.get('grid_density', DEFAULT_GRID_DENSITY)
        grid_size = GRID_DENSITY_MAPPING.get(grid_density, 21)
        
        x_vals = np.linspace(-10, 10, grid_size)
        y_vals = np.linspace(-10, 10, grid_size)
        
        x_grid, y_grid = [], []
        for y in y_vals:
            for x in x_vals:
                x_grid.append(x)
                y_grid.append(y)
        
        fig.add_trace(go.Scatter(
            x=x_grid, y=y_grid,
            mode='markers',
            marker=dict(size=3, color='rgba(0,0,0,0)'),
            showlegend=False,
            hoverinfo='none'
        ))
        
        if current_x is not None and current_y is not None:
            fig.add_trace(go.Scatter(
                x=[current_x], y=[current_y],
                mode='markers',
                marker=dict(size=8, color='red', symbol='x'),
                showlegend=False,
                hoverinfo='none'
            ))
        
        fig.add_annotation(
            x=-8, y=0.5,
            text="Negative",
            showarrow=False,
            font=dict(size=12,color = "red"),
            xanchor="center"
        )
        fig.add_annotation(
            x=8, y=0.5,
            text="Positive",
            showarrow=False,
           font=dict(size=12,color = "red"),
            xanchor="center"
        )
        fig.add_annotation(
            x=0.5, y=-7.3,
            text="Less Intensive",
            showarrow=False,
            font=dict(size=12,color = "red"),
            textangle=90,
            xanchor="center"
        )
        fig.add_annotation(
            x=0.5, y=7.2,
            text="More Intensive",
            showarrow=False,
            font=dict(size=12,color = "red"),
            textangle=90,
            xanchor="center"
        )
        
        fig.update_layout(
            title="",
            
            xaxis=dict(
                range=[-10, 10],
                showgrid=True,
                gridcolor='lightgray',
                zeroline=True,
                zerolinecolor='black',
                dtick=5,
                tickfont=dict(size=8),
                fixedrange=True,
                scaleanchor="y",
                scaleratio=1
            ),
            
            yaxis=dict(
                range=[-10, 10],
                showgrid=True,
                gridcolor='lightgray',
                zeroline=True,
                zerolinecolor='black',
                dtick=5,
                tickfont=dict(size=8),
                fixedrange=True
            ),
            
            width=pixels_5cm,
            height=pixels_5cm,
            margin=dict(l=50, r=50, t=30, b=50),
            
            plot_bgcolor='white',
            paper_bgcolor='white',
            showlegend=False,
            hovermode=False,
            dragmode=False
        )
        
        return fig

    fig = create_chart()

    chart_key = f"sentiment_chart_{st.session_state.current_index}_{current_x}_{current_y}"
    
    clicked_data = st.plotly_chart(
        fig,
        use_container_width=False,
        config={
            'displayModeBar': False,
            'staticPlot': False,
            'displaylogo': False,
            'responsive': False
        },
        on_select="rerun",
        key=chart_key
    )

    if clicked_data and 'selection' in clicked_data:
        if clicked_data['selection']['points']:
            point = clicked_data['selection']['points'][0]
            x_coord = round(point['x'], 1)
            y_coord = round(point['y'], 1)
            st.session_state.sentiment_x = x_coord
            st.session_state.sentiment_y = y_coord
            st.rerun()

    if current_x is not None and current_y is not None:
        st.success(f"**Selected Coordinates: X = {current_x}, Y = {current_y}**")

    st.markdown(f"""
    <style>
        .plotly-graph-div {{
            width: {pixels_5cm}px !important;
            height: {pixels_5cm}px !important;
        }}
        
        .stPlotlyChart > div {{
            width: {pixels_5cm}px !important;
            height: {pixels_5cm}px !important;
            margin: 0 auto !important;
        }}
    </style>
    """, unsafe_allow_html=True)


def render_navigation():
    """Render navigation controls."""
    if st.session_state.poems_df is None:
        return
    
    total_poems = len(st.session_state.poems_df)
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
    
    with col1:
        if st.button("⬅️ Prev", disabled=st.session_state.current_index <= 0):
            st.session_state.current_index -= 1
            fetch_and_parse_current_poem()
            st.rerun()
    
    with col2:
        if st.button("➡️ Next", disabled=st.session_state.current_index >= total_poems - 1):
            st.session_state.current_index += 1
            fetch_and_parse_current_poem()
            st.rerun()
    
    with col3:
        if st.button("⏭️ Skip"):
            st.session_state.current_index = min(st.session_state.current_index + 1, total_poems - 1)
            fetch_and_parse_current_poem()
            st.rerun()
    
    with col4:
        if st.button("🔄 Reload"):
            fetch_and_parse_current_poem()
            st.rerun()
    
    with col5:
        if st.session_state.current_poem_meta:
            current_url = st.session_state.current_poem_meta.url
            st.link_button("🔗 Open Source Page", current_url)


def render_poem_display():
    """Render the poem content."""
    if st.session_state.extraction_error:
        st.error(f"Error loading poem: {st.session_state.extraction_error}")
        st.info("You can still navigate to other poems or try reloading this one.")
        return
    
    if not st.session_state.current_poem_meta or not st.session_state.current_poem_text:
        st.info("No poem loaded. Please select a CSV file with poem URLs.")
        return
    
    meta = st.session_state.current_poem_meta
    text = st.session_state.current_poem_text
    
    if meta.title:
        st.title(meta.title)
    else:
        st.title("Untitled Poem")
    
    if meta.author:
        if meta.author_href:
            st.markdown(f"**By:** [{meta.author}]({meta.author_href})")
        else:
            st.markdown(f"**By:** {meta.author}")
    
    current_row = None
    if st.session_state.poems_df is not None:
        current_row = st.session_state.poems_df.iloc[st.session_state.current_index]
        
        # Create info line with year and group
        info_parts = []
        if 'year' in current_row and pd.notna(current_row['year']):
            info_parts.append(f"**Year:** {current_row['year']}")
        if 'group' in current_row and pd.notna(current_row['group']):
            info_parts.append(f"**Group:** {current_row['group']}")
        
        if info_parts:
            st.markdown(" | ".join(info_parts))
    
    # Dates
    date_info = []
    if meta.date_published:
        date_info.append(f"Published: {meta.date_published}")
    if meta.date_modified:
        date_info.append(f"Modified: {meta.date_modified}")
    
    if date_info:
        st.caption(" | ".join(date_info))
    
    # Poem text
    if text.text:
        st.subheader("Poem Text")
        # Use code block to preserve formatting
        st.code(text.text, language=None)
    else:
        st.warning("No poem text could be extracted.")
    
    # Show themes only in staged mode and after poem stage
    if st.session_state.timing_method == "staged" and st.session_state.current_stage in ["themes", "mood", "chart", "notes"]:
        # Metadata
        col1, col2 = st.columns(2)
        
        with col1:
            if meta.themes:
                st.subheader("Themes")
                for theme in meta.themes:
                    st.badge(theme)
            
            if meta.public_domain:
                st.success("✅ Public Domain")
        
        with col2:
            if meta.about:
                st.subheader("About This Poem")
                st.write(meta.about)
    elif st.session_state.timing_method == "once":
        # Show all metadata in invisible mode
        col1, col2 = st.columns(2)
        
        with col1:
            if meta.themes:
                st.subheader("Themes")
                for theme in meta.themes:
                    st.badge(theme)
            
            if meta.public_domain:
                st.success("✅ Public Domain")
        
        with col2:
            if meta.about:
                st.subheader("About This Poem")
                st.write(meta.about)


def render_coding_panel():
    """Render the coding input panel."""
    if not st.session_state.current_poem_meta:
        return
    
    # Show different content based on timing method and stage
    if st.session_state.timing_method == "staged":
        render_staged_coding_panel()
    else:
        render_full_coding_panel()

def render_staged_coding_panel():
    """Render the staged coding panel."""
    st.subheader("🏷️ Coding Panel")
    
    # Show stage progress
    stages = ["poem", "themes", "mood", "chart", "notes"]
    current_stage_idx = stages.index(st.session_state.current_stage)
    
    # Stage progress indicator
    st.write("**Current Stage:**")
    cols = st.columns(len(stages))
    for i, stage in enumerate(stages):
        with cols[i]:
            if i < current_stage_idx:
                st.success(f"✅ {stage.title()}")
            elif i == current_stage_idx:
                st.info(f"🔄 {stage.title()}")
            else:
                st.write(f"⏳ {stage.title()}")
    
    # Show stage-specific content
    if st.session_state.current_stage == "poem":
        render_poem_stage()
    elif st.session_state.current_stage == "themes":
        render_themes_stage()
    elif st.session_state.current_stage == "mood":
        render_mood_stage()
    elif st.session_state.current_stage == "chart":
        render_chart_stage()
    elif st.session_state.current_stage == "notes":
        render_notes_stage()

def render_poem_stage():
    """Render the poem reading stage."""
    st.info("📖 **Stage 1: Read the Poem** - Take your time to read and understand the poem.")
    
    if st.button("✅ Finished Reading - Go to Themes", type="primary"):
        stop_stage_timer()
        start_stage_timer("themes")
        st.rerun()

def render_themes_stage():
    """Render the themes selection stage."""
    st.info("🏷️ **Stage 2: Select Themes** - Choose relevant thematic tags.")
    
    # Apply custom styling
    apply_tag_style()
    
    # Load existing record if available
    current_url = st.session_state.current_poem_meta.url
    existing_record = latest_record_for_coder(current_url, st.session_state.coder_id)
    default_tags = existing_record.tags if existing_record else []
    
    # Tag selection (full functionality for staged mode)
    st.subheader("📝 Tag Selection")
    
    tag_option = st.radio(
        "Choose tag set:",
        options=["top20", "top50"],
        format_func=lambda x: "Top 20 Tags" if x == "top20" else "Top 50 Tags",
        index=0 if st.session_state.tag_set_preference == "top20" else 1,
        horizontal=True,
        key="staged_tag_set_radio"
    )
    
    if tag_option != st.session_state.tag_set_preference:
        st.session_state.tag_set_preference = tag_option
    
    display_tags = TOP_20_TAGS if tag_option == "top20" else TOP_50_TAGS
    
    # Initialize selected_tags from session state
    if 'staged_selected_tags' not in st.session_state:
        st.session_state.staged_selected_tags = []
    
    selected_tags = []
    
    # Display main tags and collect selections
    num_columns = st.session_state.tag_columns
    for row in range(0, len(display_tags), num_columns):
        cols = st.columns(num_columns)
        for col_idx, tag in enumerate(display_tags[row:row+num_columns]):
            with cols[col_idx]:
                is_default_selected = tag in default_tags
                checkbox_key = f"staged_main_tag_{tag}"
                is_checked = st.checkbox(tag, value=is_default_selected, key=checkbox_key)
                if is_checked:
                    selected_tags.append(tag)
    
    # Search & Add More Tags section
    with st.expander("🔍 Search & Add More Tags"):
        search_term = st.text_input(
            "Search for additional tags:",
            placeholder="Type to search through all available tags...",
            key="staged_search_input"
        )
        
        if search_term:
            matching_tags = [tag for tag in ALL_CORPUS_TAGS 
                           if search_term.lower() in tag.lower() and tag not in selected_tags and tag not in display_tags]
            
            if matching_tags:
                st.write(f"Found {len(matching_tags)} additional matching tags:")
                search_columns = min(st.session_state.tag_columns, len(matching_tags))
                cols = st.columns(search_columns)
                for i, tag in enumerate(matching_tags[:12]):  # Limit to 12 results
                    with cols[i % search_columns]:
                        search_checkbox_key = f"staged_search_tag_{tag}"
                        is_checked = st.checkbox(f"{tag}", key=search_checkbox_key)
                        if is_checked:
                            selected_tags.append(tag)
            else:
                st.write("No additional matching tags found.")
        
        custom_tag_input = st.text_input(
            "Add custom tag:",
            placeholder="Enter tags separated by commas (e.g., tag1, tag2, tag3)...",
            help="Use this for tags not found in the standard corpus. Separate multiple tags with commas.",
            key="staged_custom_tag_input"
        )
        
        if custom_tag_input.strip():
            # Split by comma and add each tag
            custom_tags = [tag.strip() for tag in custom_tag_input.split(',') if tag.strip()]
            for custom_tag in custom_tags:
                if custom_tag not in selected_tags:
                    selected_tags.append(custom_tag)
    
    # Update session state with current selections
    st.session_state.staged_selected_tags = selected_tags
    
    # Display selection summary
    if selected_tags:
        st.info(f"✅ Selected {len(selected_tags)} tags: {', '.join(selected_tags[:5])}{'...' if len(selected_tags) > 5 else ''}")
    else:
        st.info("No tags selected yet")
    
    if st.button("✅ Finished Themes - Go to Mood", type="primary"):
        stop_stage_timer()
        start_stage_timer("mood")
        st.rerun()

def render_mood_stage():
    """Render the mood selection stage."""
    st.info("🎭 **Stage 3: Select Moods** - Choose emotional categories.")
    
    # Apply custom styling
    apply_tag_style()
    
    # Load existing record if available
    current_url = st.session_state.current_poem_meta.url
    existing_record = latest_record_for_coder(current_url, st.session_state.coder_id)
    default_moods = existing_record.moods if existing_record else []
    
    st.subheader("🎭 Mood Tags")
    selected_moods = []
    
    num_columns = st.session_state.tag_columns
    mood_rows = [MOOD_OPTIONS[i:i+num_columns] for i in range(0, len(MOOD_OPTIONS), num_columns)]
    for mood_row in mood_rows:
        cols = st.columns(num_columns)
        for col_idx, mood in enumerate(mood_row):
            with cols[col_idx]:
                is_default_selected = mood in default_moods
                mood_checkbox_key = f"staged_mood_{mood}"
                if st.checkbox(mood.capitalize(), value=is_default_selected, key=mood_checkbox_key):
                    selected_moods.append(mood)
    
    # Custom mood tags section
    with st.expander("🔍 Add Custom Mood Tags"):
        custom_mood_input = st.text_input(
            "Add custom mood:",
            placeholder="Enter moods separated by commas (e.g., melancholy, euphoria, nostalgia)...",
            help="Use this for mood tags not found in the standard options. Separate multiple moods with commas.",
            key="staged_custom_mood_input"
        )
        
        if custom_mood_input.strip():
            # Split by comma and add each mood
            custom_moods = [mood.strip() for mood in custom_mood_input.split(',') if mood.strip()]
            for custom_mood in custom_moods:
                if custom_mood not in selected_moods:
                    selected_moods.append(custom_mood)
    
    # Store selected moods in session state
    st.session_state.staged_selected_moods = selected_moods
    
    # Display selection summary
    if selected_moods:
        st.info(f"✅ Selected {len(selected_moods)} moods: {', '.join(selected_moods[:5])}{'...' if len(selected_moods) > 5 else ''}")
    else:
        st.info("No moods selected yet")
    
    if st.button("✅ Finished Moods - Go to Chart", type="primary"):
        stop_stage_timer()
        start_stage_timer("chart")
        st.rerun()

def render_chart_stage():
    """Render the sentiment chart stage."""
    st.info("📊 **Stage 4: Set Sentiment Coordinates** - Click on the chart to set coordinates.")
    
    # Load existing coordinates if available
    current_url = st.session_state.current_poem_meta.url
    existing_record = latest_record_for_coder(current_url, st.session_state.coder_id)
    
    if existing_record and not st.session_state.just_saved_and_reset:
        st.session_state.sentiment_x = getattr(existing_record, 'sentiment_x', 0.0)
        st.session_state.sentiment_y = getattr(existing_record, 'sentiment_y', 0.0)
    
    render_sentiment_2d()
    
    if st.button("✅ Finished Chart - Go to Notes", type="primary"):
        stop_stage_timer()
        start_stage_timer("notes")
        st.rerun()

def render_notes_stage():
    """Render the notes and final submission stage."""
    st.info("📝 **Stage 5: Add Notes & Submit** - Add any additional observations and submit.")
    
    # Load existing record if available
    current_url = st.session_state.current_poem_meta.url
    existing_record = latest_record_for_coder(current_url, st.session_state.coder_id)
    default_notes = existing_record.notes if existing_record else ""
    
    with st.form("staged_coding_form", clear_on_submit=False):
        notes = st.text_area(
            "Notes",
            value=default_notes,
            height=100,
            key="staged_notes_input"
        )
        
        submitted = st.form_submit_button("💾 Save & Complete", type="primary")
        
        if submitted:
            if not st.session_state.coder_id.strip():
                st.error("Please enter a Coder ID first")
                return
            
            # Stop final stage timer
            stop_stage_timer()
            
            # Get all staged data
            all_tags = st.session_state.get('staged_selected_tags', [])
            selected_moods = st.session_state.get('staged_selected_moods', [])
            
            current_csv_row = st.session_state.poems_df.iloc[st.session_state.current_index]
            html_content = st.session_state.current_poem_text.raw_html if st.session_state.current_poem_text else ""
            
            # Calculate total time
            total_time = sum(st.session_state.stage_timings.values())
            
            record = CodingRecord(
                timestamp_iso=datetime.now().isoformat(),
                coder_id=st.session_state.coder_id.strip(),
                url=current_url,
                poem_uuid=st.session_state.current_poem_meta.poem_uuid,
                title=st.session_state.current_poem_meta.title,
                author=st.session_state.current_poem_meta.author,
                year=str(current_csv_row.get('year', '')) if pd.notna(current_csv_row.get('year')) else None,
                group=str(current_csv_row.get('group', '')) if pd.notna(current_csv_row.get('group')) else None,
                author_url=str(current_csv_row.get('author_url', '')) if pd.notna(current_csv_row.get('author_url')) else None,
                tags=all_tags,
                moods=selected_moods,
                sentiment_x=st.session_state.sentiment_x,
                sentiment_y=st.session_state.sentiment_y,
                notes=notes.strip(),
                is_complete=True,
                html_sha1=sha1(html_content),
                extraction_ok=st.session_state.extraction_error is None,
                error=st.session_state.extraction_error,
                time_spent_seconds=total_time,
                stage_timings=st.session_state.stage_timings.copy()
            )
            
            try:
                save_record(record)
                st.success("✅ Saved successfully!")
                
                # Reset for next poem
                reset_stage_timings()
                start_stage_timer("poem")
                
                # Clear staged data
                if 'staged_selected_tags' in st.session_state:
                    del st.session_state['staged_selected_tags']
                if 'staged_selected_moods' in st.session_state:
                    del st.session_state['staged_selected_moods']
                
                st.session_state.sentiment_x = 0.0
                st.session_state.sentiment_y = 0.0
                
                if st.session_state.current_index < len(st.session_state.poems_df) - 1:
                    time.sleep(1)
                    st.session_state.current_index += 1
                    fetch_and_parse_current_poem()
                    st.rerun()
                else:
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Save error: {str(e)}")

def render_full_coding_panel():
    """Render the full coding panel (original functionality)."""
    if not st.session_state.current_poem_meta:
        return
    
    # Apply custom styling
    apply_tag_style()
    
    st.subheader("🏷️ Coding Panel")
    
    current_url = st.session_state.current_poem_meta.url
    
    # Load existing record if available (only for current coder)
    # But skip loading if we just saved and reset to maintain clean state
    existing_record = None
    if not st.session_state.just_saved_and_reset:
        existing_record = latest_record_for_coder(current_url, st.session_state.coder_id)
    
    # Initialize form values
    default_tags = existing_record.tags if existing_record else []
    default_sentiment = existing_record.sentiment if existing_record else "neutral"
    default_notes = existing_record.notes if existing_record else ""
    default_complete = existing_record.is_complete if existing_record else False
    
    # Load existing coordinates if available (only once per poem)
    if existing_record and not st.session_state.just_saved_and_reset and (not hasattr(st.session_state, 'coords_loaded_for_url') or st.session_state.get('coords_loaded_for_url') != current_url):
        st.session_state.sentiment_x = getattr(existing_record, 'sentiment_x', 0.0)
        st.session_state.sentiment_y = getattr(existing_record, 'sentiment_y', 0.0)
        st.session_state.coords_loaded_for_url = current_url
    
    is_fresh_reset = st.session_state.just_saved_and_reset
    
    if st.session_state.just_saved_and_reset:
        st.session_state.just_saved_and_reset = False

    st.subheader("📝 Tag Selection")
    
    tag_option = st.radio(
        "Choose tag set:",
        options=["top20", "top50"],
        format_func=lambda x: "Top 20 Tags" if x == "top20" else "Top 50 Tags",
        index=0 if st.session_state.tag_set_preference == "top20" else 1,
        horizontal=True,
        key="tag_set_radio"
    )
    
    if tag_option != st.session_state.tag_set_preference:
        st.session_state.tag_set_preference = tag_option
    
    display_tags = TOP_20_TAGS if tag_option == "top20" else TOP_50_TAGS
    
    selected_tags = []
    
    key_suffix = f"_{st.session_state.current_index}" if is_fresh_reset else ""
    
    num_columns = st.session_state.tag_columns
    for row in range(0, len(display_tags), num_columns):
        cols = st.columns(num_columns)
        for col_idx, tag in enumerate(display_tags[row:row+num_columns]):
            with cols[col_idx]:
                is_default_selected = tag in default_tags
                checkbox_key = f"main_tag_{tag}{key_suffix}"
                if st.checkbox(tag, value=is_default_selected, key=checkbox_key):
                    selected_tags.append(tag)
    
    with st.expander("🔍 Search & Add More Tags"):
        search_term = st.text_input(
            "Search for additional tags:",
            placeholder="Type to search through all available tags..."
        )
        
        if search_term:
            matching_tags = [tag for tag in ALL_CORPUS_TAGS 
                           if search_term.lower() in tag.lower() and tag not in selected_tags and tag not in display_tags]
            
            if matching_tags:
                st.write(f"Found {len(matching_tags)} additional matching tags:")
                search_columns = min(st.session_state.tag_columns, len(matching_tags))
                cols = st.columns(search_columns)
                for i, tag in enumerate(matching_tags[:12]):  # Limit to 12 results
                    with cols[i % search_columns]:
                        search_checkbox_key = f"search_tag_{tag}{key_suffix}"
                        if st.checkbox(f"{tag}", key=search_checkbox_key):
                            selected_tags.append(tag)
            else:
                st.write("No additional matching tags found.")
        
        custom_tag_input = st.text_input(
            "Add custom tag:",
            placeholder="Enter tags separated by commas (e.g., tag1, tag2, tag3)...",
            help="Use this for tags not found in the standard corpus. Separate multiple tags with commas."
        )
        
        if custom_tag_input.strip():
            # Split by comma and add each tag
            custom_tags = [tag.strip() for tag in custom_tag_input.split(',') if tag.strip()]
            for custom_tag in custom_tags:
                if custom_tag not in selected_tags:
                    selected_tags.append(custom_tag)
    
    if selected_tags:
        st.info(f"✅ Selected {len(selected_tags)} tags: {', '.join(selected_tags[:5])}{'...' if len(selected_tags) > 5 else ''}")
    else:
        st.info("No tags selected yet")
    
    st.subheader("🎭 Mood Tags")
    selected_moods = []
    
    default_moods = []
    if existing_record and hasattr(existing_record, 'moods') and existing_record.moods:
        default_moods = existing_record.moods
    
    mood_key_suffix = f"_{st.session_state.current_index}" if is_fresh_reset else ""
    
    num_columns = st.session_state.tag_columns
    mood_rows = [MOOD_OPTIONS[i:i+num_columns] for i in range(0, len(MOOD_OPTIONS), num_columns)]
    for mood_row in mood_rows:
        cols = st.columns(num_columns)
        for col_idx, mood in enumerate(mood_row):
            with cols[col_idx]:
                is_default_selected = mood in default_moods
                mood_checkbox_key = f"mood_{mood}{mood_key_suffix}"
                if st.checkbox(mood.capitalize(), value=is_default_selected, key=mood_checkbox_key):
                    selected_moods.append(mood)
    
    # Custom mood tags section
    with st.expander("🔍 Add Custom Mood Tags"):
        custom_mood_input = st.text_input(
            "Add custom mood:",
            placeholder="Enter moods separated by commas (e.g., melancholy, euphoria, nostalgia)...",
            help="Use this for mood tags not found in the standard options. Separate multiple moods with commas.",
            key=f"custom_mood_input{mood_key_suffix}"
        )
        
        if custom_mood_input.strip():
            # Split by comma and add each mood
            custom_moods = [mood.strip() for mood in custom_mood_input.split(',') if mood.strip()]
            for custom_mood in custom_moods:
                if custom_mood not in selected_moods:
                    selected_moods.append(custom_mood)
    
    # Display mood selection summary
    if selected_moods:
        st.info(f"✅ Selected {len(selected_moods)} moods: {', '.join(selected_moods[:5])}{'...' if len(selected_moods) > 5 else ''}")
    else:
        st.info("No moods selected yet")
    
    render_sentiment_2d()
    
    with st.form("coding_form", clear_on_submit=False):
        notes_key = f"notes_input_{st.session_state.current_index}" if is_fresh_reset else "notes_input"
        notes = st.text_area(
            "Notes",
            value=default_notes,
            height=100,
            key=notes_key
        )
        
        is_complete = True
        
        submitted = st.form_submit_button("💾 Save", type="primary")
        
        if submitted:
            if not st.session_state.coder_id.strip():
                st.error("Please enter a Coder ID first")
                return
            
            all_tags = selected_tags
            
            current_csv_row = st.session_state.poems_df.iloc[st.session_state.current_index]
            
            html_content = st.session_state.current_poem_text.raw_html if st.session_state.current_poem_text else ""
            
            # Stop timer and get elapsed time
            time_spent = stop_timer()
            
            record = CodingRecord(
                timestamp_iso=datetime.now().isoformat(),
                coder_id=st.session_state.coder_id.strip(),
                url=current_url,
                poem_uuid=st.session_state.current_poem_meta.poem_uuid,
                title=st.session_state.current_poem_meta.title,
                author=st.session_state.current_poem_meta.author,
                year=str(current_csv_row.get('year', '')) if pd.notna(current_csv_row.get('year')) else None,
                group=str(current_csv_row.get('group', '')) if pd.notna(current_csv_row.get('group')) else None,
                author_url=str(current_csv_row.get('author_url', '')) if pd.notna(current_csv_row.get('author_url')) else None,
                tags=all_tags,
                moods=selected_moods,
                sentiment_x=st.session_state.sentiment_x,
                sentiment_y=st.session_state.sentiment_y,
                notes=notes.strip(),
                is_complete=is_complete,
                html_sha1=sha1(html_content),
                extraction_ok=st.session_state.extraction_error is None,
                error=st.session_state.extraction_error,
                time_spent_seconds=time_spent
            )
            
            try:
                save_record(record)
                st.success("✅ Saved successfully!")
                
                keys_to_delete = []
                
                all_session_keys = list(st.session_state.keys())
                for key in all_session_keys:
                    if key.startswith('main_tag_') or key.startswith('search_tag_'):
                        keys_to_delete.append(key)
                    elif key.startswith('mood_'):
                        keys_to_delete.append(key)
                    elif key.startswith('sentiment_chart'):
                        keys_to_delete.append(key)
                    elif key.startswith('notes_input'):
                        keys_to_delete.append(key)
                
                for key in keys_to_delete:
                    try:
                        if key in st.session_state:
                            del st.session_state[key]
                    except KeyError:
                        pass
                
                st.session_state.sentiment_x = 0.0
                st.session_state.sentiment_y = 0.0
                
                if 'coords_loaded_for_url' in st.session_state:
                    del st.session_state['coords_loaded_for_url']
                
                st.session_state.just_saved_and_reset = True
                
                if st.session_state.current_index < len(st.session_state.poems_df) - 1:
                    time.sleep(1)
                    st.session_state.current_index += 1
                    fetch_and_parse_current_poem()
                    st.rerun()
                else:
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Save error: {str(e)}")


def main():
    """Main application function."""
    initialize_session_state()
    
    render_sidebar()
    
    st.title("📝 Poem Sentiment Coding")
    
    # Only show content if coder ID is entered
    if not st.session_state.coder_id.strip():
        st.info("👋 Please enter your Coder ID in the sidebar to begin coding poems.")
        st.markdown("""
        ### How to use this tool:
        1. Enter your unique Coder ID in the sidebar
        2. Choose your timing method (Count once or count on each stage)
        3. The system will automatically load your progress
        4. Start coding poems using the interface on the right
        5. Your progress will be automatically saved
        """)
        return
    
    render_navigation()
    
    st.divider()
    
    with st.sidebar:
        st.subheader("⚙️ Layout Settings")
        layout_ratio = st.select_slider(
            "Column Width Ratio",
            options=[
                "1:1", "3:2", "2:1", "5:2", "3:1", "4:1"
            ],
            value="2:1",
            help="Choose the width ratio between poem display area and coding panel"
        )
        
        left_ratio, right_ratio = map(int, layout_ratio.split(':'))
        
    col1, col2 = st.columns([left_ratio, right_ratio])
    
    with col1:
        render_poem_display()
    
    with col2:
        render_coding_panel()


if __name__ == "__main__":
    main()
