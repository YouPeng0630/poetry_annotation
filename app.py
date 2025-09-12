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

from models import CodingRecord
from scraper import fetch_html, parse_poem
from storage import save_record, latest_record_for, get_coding_stats
from utils import sha1, normalize_tags


# Page configuration
st.set_page_config(
    page_title="Poem Qualitative Coding",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Comprehensive tag collections based on corpus analysis
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
    'anxiety', 'weather', 'illness', 'home'
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

# Default to top 20 for cleaner interface
DEFAULT_BASE_TAGS = TOP_20_TAGS

# Mood options - replacing sentiment
MOOD_OPTIONS = ["anger", "anticipation", "disgust", "fear", "joy", "sadness", "surprise", "trust"]

# Sentiment options (kept for backward compatibility)
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
                        # Only count records for this specific coder
                        if (record.get('coder_id') == coder_id.strip() and 
                            record.get('is_complete', False)):
                            completed_urls.add(record.get('url'))
                    except json.JSONDecodeError:
                        continue
        
        return len(completed_urls)
    except Exception:
        return 0


def get_last_completed_index():
    """Get the index of the last completed poem to resume from next uncompleted one."""
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
                        if record.get('is_complete', False):
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
        # Start from index 0, will be updated when coder ID is entered
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


def load_poets_csv(file_path: str) -> Optional[pd.DataFrame]:
    """Load and validate poets CSV file."""
    try:
        if not os.path.exists(file_path):
            st.error(f"File not found: {file_path}")
            return None
        
        df = pd.read_csv(file_path)
        
        # Find URL column
        url_columns = ['url', 'URL', 'link', 'href']
        url_column = None
        for col in url_columns:
            if col in df.columns:
                url_column = col
                break
        
        if url_column is None:
            st.error(f"No URL column found. Expected one of: {', '.join(url_columns)}")
            return None
        
        # Standardize column name
        if url_column != 'url':
            df = df.rename(columns={url_column: 'url'})
        
        # Filter out empty URLs and deduplicate
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


def fetch_and_parse_current_poem():
    """Fetch and parse the current poem."""
    if st.session_state.poems_df is None or len(st.session_state.poems_df) == 0:
        return
    
    current_url = st.session_state.poems_df.iloc[st.session_state.current_index]['url']
    
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
    
    # Load CSV automatically
    csv_path = "poets.csv"
    if os.path.exists(csv_path):
        if st.session_state.poems_df is None:
            df_to_load = load_poets_csv(csv_path)
            if df_to_load is not None:
                st.session_state.poems_df = df_to_load
                st.session_state.current_index = 0
                fetch_and_parse_current_poem()
    else:
        st.sidebar.error("poets.csv file not found")
    
    # Coder ID
    previous_coder_id = st.session_state.coder_id
    st.session_state.coder_id = st.sidebar.text_input(
        "Coder ID", 
        value=st.session_state.coder_id
    )
    
    # If coder ID changed and is not empty, jump to their last position
    if (st.session_state.coder_id != previous_coder_id and 
        st.session_state.coder_id.strip() != ""):
        new_index = get_last_completed_index_for_coder(st.session_state.coder_id)
        if new_index != st.session_state.current_index:
            st.session_state.current_index = new_index
            fetch_and_parse_current_poem()
            st.rerun()
    
    # Progress
    if st.session_state.poems_df is not None:
        st.sidebar.subheader("📊 Progress")
        total_poems = len(st.session_state.poems_df)
        current_pos = st.session_state.current_index + 1
        
        stats = get_coding_stats()
        
        st.sidebar.metric("Current Position", f"{current_pos} / {total_poems}")
        st.sidebar.metric("Completed", stats['completed_records'])
        
        # Progress bar
        progress = current_pos / total_poems
        st.sidebar.progress(progress)


def render_sentiment_2d():
    """Render interactive 2D coordinate chart using Plotly."""
    st.subheader("Sentiment Coordinates")
    
    # Get current coordinates
    current_x = st.session_state.get('sentiment_x', 0.0)
    current_y = st.session_state.get('sentiment_y', 0.0)
    
    st.write("**Click anywhere on the chart to set coordinates:**")
    
    # DPI setting (default 96)
    dpi = 200

    def cm_to_pixels(cm, dpi):
        return int(cm / 2.54 * dpi)

    pixels_5cm = cm_to_pixels(5, dpi)

    def create_chart():
        fig = go.Figure()
        
        # Create invisible grid for clicking
        grid_size = 21
        x_vals = np.linspace(-10, 10, grid_size)
        y_vals = np.linspace(-10, 10, grid_size)
        
        # Generate grid points
        x_grid, y_grid = [], []
        for y in y_vals:
            for x in x_vals:
                x_grid.append(x)
                y_grid.append(y)
        
        # Invisible clickable points
        fig.add_trace(go.Scatter(
            x=x_grid, y=y_grid,
            mode='markers',
            marker=dict(size=3, color='rgba(0,0,0,0)'),
            showlegend=False,
            hoverinfo='none'
        ))
        
        # Show current point
        if current_x is not None and current_y is not None:
            fig.add_trace(go.Scatter(
                x=[current_x], y=[current_y],
                mode='markers',
                marker=dict(size=8, color='red', symbol='x'),
                showlegend=False,
                hoverinfo='none'
            ))
        
        # Add axis labels at the ends
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
        
        # Chart layout
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

    # Create and display chart
    fig = create_chart()

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
        key="sentiment_chart"
    )

    # Process clicks
    if clicked_data and 'selection' in clicked_data:
        if clicked_data['selection']['points']:
            point = clicked_data['selection']['points'][0]
            x_coord = round(point['x'], 1)
            y_coord = round(point['y'], 1)
            st.session_state.sentiment_x = x_coord
            st.session_state.sentiment_y = y_coord
            st.rerun()

    # Display coordinates (minimal)
    if current_x is not None and current_y is not None:
        st.success(f"**Selected Coordinates: X = {current_x}, Y = {current_y}**")

    # CSS for exact sizing
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
    
    # Poem header
    if meta.title:
        st.title(meta.title)
    else:
        st.title("Untitled Poem")
    
    # Author with link if available
    if meta.author:
        if meta.author_href:
            st.markdown(f"**By:** [{meta.author}]({meta.author_href})")
        else:
            st.markdown(f"**By:** {meta.author}")
    
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


def render_coding_panel():
    """Render the coding input panel."""
    if not st.session_state.current_poem_meta:
        return
    
    st.subheader("🏷️ Coding Panel")
    
    current_url = st.session_state.current_poem_meta.url
    
    # Load existing record if available
    existing_record = latest_record_for(current_url)
    
    # Initialize form values
    default_tags = existing_record.tags if existing_record else []
    default_sentiment = existing_record.sentiment if existing_record else "neutral"
    default_notes = existing_record.notes if existing_record else ""
    default_complete = existing_record.is_complete if existing_record else False
    
    # Load existing coordinates if available (only once per poem)
    if existing_record and not hasattr(st.session_state, 'coords_loaded_for_url') or st.session_state.get('coords_loaded_for_url') != current_url:
        st.session_state.sentiment_x = getattr(existing_record, 'sentiment_x', 0.0)
        st.session_state.sentiment_y = getattr(existing_record, 'sentiment_y', 0.0)
        st.session_state.coords_loaded_for_url = current_url
    

    
    # Tag selection with checkboxes (outside of form for real-time updates)
    st.subheader("📝 Tag Selection")
    
    # Display TOP_20_TAGS as checkboxes in a 4-column grid
    selected_tags = []
    
    # Create checkbox grid for TOP_20_TAGS (4 per row)
    for row in range(0, len(TOP_20_TAGS), 4):
        cols = st.columns(4)
        for col_idx, tag in enumerate(TOP_20_TAGS[row:row+4]):
            with cols[col_idx]:
                # Check if this tag was previously selected
                is_default_selected = tag in default_tags
                if st.checkbox(tag, value=is_default_selected, key=f"main_tag_{tag}"):
                    selected_tags.append(tag)
    
    # Search and add functionality  
    with st.expander("🔍 Search & Add More Tags"):
        search_term = st.text_input(
            "Search for additional tags:",
            placeholder="Type to search through all available tags..."
        )
        
        if search_term:
            # Search through ALL_CORPUS_TAGS but exclude already selected ones
            matching_tags = [tag for tag in ALL_CORPUS_TAGS 
                           if search_term.lower() in tag.lower() and tag not in selected_tags and tag not in TOP_20_TAGS]
            
            if matching_tags:
                st.write(f"Found {len(matching_tags)} additional matching tags:")
                # Show matching tags as checkboxes for selection
                cols = st.columns(min(3, len(matching_tags)))
                for i, tag in enumerate(matching_tags[:12]):  # Limit to 12 results
                    with cols[i % 3]:
                        if st.checkbox(f"{tag}", key=f"search_tag_{tag}"):
                            selected_tags.append(tag)
            else:
                st.write("No additional matching tags found.")
        
        # Manual tag input for completely custom tags
        custom_tag_input = st.text_input(
            "Add custom tag:",
            placeholder="Enter a new tag not in the corpus...",
            help="Use this for tags not found in the standard corpus"
        )
        
        # Add custom tag to the list if provided
        if custom_tag_input.strip() and custom_tag_input.strip() not in selected_tags:
            selected_tags.append(custom_tag_input.strip())
    
    # Show selected tags count (after all selections are processed)
    if selected_tags:
        st.info(f"✅ Selected {len(selected_tags)} tags: {', '.join(selected_tags[:5])}{'...' if len(selected_tags) > 5 else ''}")
    else:
        st.info("No tags selected yet")
    
    # Mood selection with checkboxes
    st.subheader("🎭 Mood Tags")
    selected_moods = []
    
    # Load existing moods if available
    default_moods = []
    if existing_record and hasattr(existing_record, 'moods') and existing_record.moods:
        default_moods = existing_record.moods
    
    # Create checkbox grid for moods (4 per row)
    mood_rows = [MOOD_OPTIONS[i:i+4] for i in range(0, len(MOOD_OPTIONS), 4)]
    for mood_row in mood_rows:
        cols = st.columns(4)
        for col_idx, mood in enumerate(mood_row):
            with cols[col_idx]:
                is_default_selected = mood in default_moods
                if st.checkbox(mood.capitalize(), value=is_default_selected, key=f"mood_{mood}"):
                    selected_moods.append(mood)
    
    # 2D Sentiment coordinates (outside of form)
    render_sentiment_2d()
    
    # Form for other inputs
    with st.form("coding_form", clear_on_submit=True):
        # Notes
        notes = st.text_area(
            "Notes",
            value=default_notes,
            height=100
        )
        
        # Complete checkbox
        is_complete = st.checkbox(
            "Mark as Complete",
            value=default_complete
        )
        
        # Save button
        submitted = st.form_submit_button("💾 Save", type="primary")
    
        if submitted:
            if not st.session_state.coder_id.strip():
                st.error("Please enter a Coder ID first")
                return
            
            # Use selected tags directly (they're already processed)
            all_tags = selected_tags
            
            # Create coding record
            html_content = st.session_state.current_poem_text.raw_html if st.session_state.current_poem_text else ""
            
            record = CodingRecord(
                timestamp_iso=datetime.now().isoformat(),
                coder_id=st.session_state.coder_id.strip(),
                url=current_url,
                poem_uuid=st.session_state.current_poem_meta.poem_uuid,
                title=st.session_state.current_poem_meta.title,
                author=st.session_state.current_poem_meta.author,
                tags=all_tags,
                moods=selected_moods,
                sentiment_x=st.session_state.sentiment_x,
                sentiment_y=st.session_state.sentiment_y,
                notes=notes.strip(),
                is_complete=is_complete,
                html_sha1=sha1(html_content),
                extraction_ok=st.session_state.extraction_error is None,
                error=st.session_state.extraction_error
            )
            
            try:
                save_record(record)
                st.success("✅ Saved successfully!")
                
                # Clear tag and mood selections after successful save
                # Delete checkbox keys to force recreation with cleared state
                keys_to_delete = []
                
                # Collect tag checkbox keys that actually exist
                for tag in TOP_20_TAGS + ALL_CORPUS_TAGS:
                    main_key = f"main_tag_{tag}"
                    search_key = f"search_tag_{tag}"
                    if main_key in st.session_state:
                        keys_to_delete.append(main_key)
                    if search_key in st.session_state:
                        keys_to_delete.append(search_key)
                
                # Collect mood checkbox keys that actually exist
                for mood in MOOD_OPTIONS:
                    mood_key = f"mood_{mood}"
                    if mood_key in st.session_state:
                        keys_to_delete.append(mood_key)
                
                # Safely delete all the existing keys
                for key in keys_to_delete:
                    try:
                        if key in st.session_state:
                            del st.session_state[key]
                    except KeyError:
                        pass  # Key doesn't exist, skip it
                
                # Reset coordinates
                st.session_state.sentiment_x = 0.0
                st.session_state.sentiment_y = 0.0
                
                # Auto-advance if complete and not at end
                if is_complete and st.session_state.current_index < len(st.session_state.poems_df) - 1:
                    time.sleep(1)
                    st.session_state.current_index += 1
                    fetch_and_parse_current_poem()
                    st.rerun()
                else:
                    # If not auto-advancing, still rerun to show cleared selections
                    st.rerun()
                    
            except Exception as e:
                st.error(f"Save error: {str(e)}")


def main():
    """Main application function."""
    initialize_session_state()
    
    # Sidebar
    render_sidebar()
    
    # Main content
    st.title("📝 Poem Sentiment Coding")
    
    # Navigation
    render_navigation()
    
    st.divider()
    
    # Two-column layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        render_poem_display()
    
    with col2:
        render_coding_panel()


if __name__ == "__main__":
    main()
