import streamlit as st
import plotly.graph_objects as go
import numpy as np

# Try to import streamlit-plotly-events
try:
    from streamlit_plotly_events import plotly_events
    PLOTLY_EVENTS_AVAILABLE = True
except ImportError:
    PLOTLY_EVENTS_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Sentiment Coordinate Selector",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if 'sentiment_x' not in st.session_state:
    st.session_state.sentiment_x = 0.0
if 'sentiment_y' not in st.session_state:
    st.session_state.sentiment_y = 0.0

def render_sentiment_chart():
    """Render the clickable sentiment coordinate chart."""
    current_x = st.session_state.get('sentiment_x', 0.0)
    current_y = st.session_state.get('sentiment_y', 0.0)
    
    # Create the plotly figure
    fig = go.Figure()
    
    # Add grid lines
    grid_range = np.arange(-9.5, 10, 0.5)
    
    # Add fine grid lines (every 0.5 units)
    for x in grid_range:
        fig.add_shape(
            type="line",
            x0=x, y0=-9.5, x1=x, y1=9.5,
            line=dict(color="lightgray", width=0.5),
            layer="below"
        )
    
    for y in grid_range:
        fig.add_shape(
            type="line",
            x0=-9.5, y0=y, x1=9.5, y1=y,
            line=dict(color="lightgray", width=0.5),
            layer="below"
        )
    
    # Add main grid lines (every 1 unit)
    main_grid_range = np.arange(-9, 10, 1)
    for x in main_grid_range:
        fig.add_shape(
            type="line",
            x0=x, y0=-9.5, x1=x, y1=9.5,
            line=dict(color="gray", width=1),
            layer="below"
        )
    
    for y in main_grid_range:
        fig.add_shape(
            type="line",
            x0=-9.5, y0=y, x1=9.5, y1=y,
            line=dict(color="gray", width=1),
            layer="below"
        )
    
    # Add axes
    fig.add_shape(
        type="line",
        x0=-9.5, y0=0, x1=9.5, y1=0,
        line=dict(color="black", width=3),
        layer="below"
    )
    fig.add_shape(
        type="line",
        x0=0, y0=-9.5, x1=0, y1=9.5,
        line=dict(color="black", width=3),
        layer="below"
    )
    
    # Add axis labels as annotations
    fig.add_annotation(
        x=-8, y=-0.5,
        text="Negative",
        showarrow=False,
        font=dict(color="red", size=14, family="Arial Black"),
        bgcolor="white",
        bordercolor="red",
        borderwidth=1
    )
    
    fig.add_annotation(
        x=8, y=-0.5,
        text="Positive", 
        showarrow=False,
        font=dict(color="red", size=14, family="Arial Black"),
        bgcolor="white",
        bordercolor="red",
        borderwidth=1
    )
    
    fig.add_annotation(
        x=0.5, y=8,
        text="More<br>Intensive",
        showarrow=False,
        font=dict(color="red", size=14, family="Arial Black"),
        bgcolor="white",
        bordercolor="red",
        borderwidth=1,
        textangle=-90
    )
    
    fig.add_annotation(
        x=0.5, y=-8,
        text="Less<br>Intensive",
        showarrow=False,
        font=dict(color="red", size=14, family="Arial Black"),
        bgcolor="white",
        bordercolor="red",
        borderwidth=1,
        textangle=-90
    )
    
    # Add current point if not at origin
    if current_x != 0.0 or current_y != 0.0:
        fig.add_trace(go.Scatter(
            x=[current_x],
            y=[current_y],
            mode='markers',
            marker=dict(
                size=20,
                color='red',
                symbol='x',
                line=dict(width=3, color='darkred')
            ),
            name='Current Selection',
            showlegend=False,
            hovertemplate=f'<b>Selected Point</b><br>X: {current_x:.1f}<br>Y: {current_y:.1f}<extra></extra>'
        ))
        
        # Add circle around selected point
        fig.add_shape(
            type="circle",
            x0=current_x-0.3, y0=current_y-0.3,
            x1=current_x+0.3, y1=current_y+0.3,
            line=dict(color="blue", width=2),
            fillcolor="rgba(0,100,255,0.1)"
        )
    
    # Add invisible scatter plot to capture all clicks
    click_x = []
    click_y = []
    for x in np.arange(-9.5, 9.6, 0.1):
        for y in np.arange(-9.5, 9.6, 0.1):
            click_x.append(x)
            click_y.append(y)
    
    fig.add_trace(go.Scatter(
        x=click_x,
        y=click_y,
        mode='markers',
        marker=dict(
            size=1,
            color='rgba(0,0,0,0)',  # Transparent
            opacity=0
        ),
        name='Click Area',
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # Configure layout
    fig.update_layout(
        title=dict(
            text="Click anywhere to set sentiment coordinates",
            x=0.5,
            font=dict(size=16)
        ),
        xaxis=dict(
            range=[-9.7, 9.7],
            title="",
            showgrid=False,
            zeroline=False,
            tickmode='linear',
            dtick=2,
            tickfont=dict(size=12)
        ),
        yaxis=dict(
            range=[-9.7, 9.7],
            title="",
            showgrid=False,
            zeroline=False,
            tickmode='linear', 
            dtick=2,
            tickfont=dict(size=12)
        ),
        width=600,
        height=600,
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    return fig

def main():
    st.title("🎯 Sentiment Coordinate Selector")
    st.markdown("**Interactive tool for selecting sentiment coordinates**")
    
    # Check if streamlit-plotly-events is available
    if not PLOTLY_EVENTS_AVAILABLE:
        st.error("**Required package not installed!**")
        st.markdown("""
        This app requires `streamlit-plotly-events` to work properly.
        
        **To install:**
        ```bash
        pip install streamlit-plotly-events
        ```
        
        After installation, restart the app.
        """)
        st.stop()
    
    # Create and display the chart
    fig = render_sentiment_chart()
    
    # Capture click events using streamlit-plotly-events
    selected_points = plotly_events(
        fig,
        click_event=True,
        hover_event=False,
        select_event=False,
        override_height=600,
        override_width=600,
        key="sentiment_chart"
    )
    
    # Process click events
    current_x = st.session_state.get('sentiment_x', 0.0)
    current_y = st.session_state.get('sentiment_y', 0.0)
    
    if selected_points:
        point = selected_points[0]  # Get the first clicked point
        clicked_x = point['x']
        clicked_y = point['y']
        
        # Round to precision of 0.1
        new_x = round(clicked_x, 1)
        new_y = round(clicked_y, 1)
        
        # Constrain to valid range
        new_x = max(-9.5, min(9.5, new_x))
        new_y = max(-9.5, min(9.5, new_y))
        
        # Update session state if coordinates changed
        if new_x != current_x or new_y != current_y:
            st.session_state.sentiment_x = new_x
            st.session_state.sentiment_y = new_y
            st.rerun()
    
    # Display current selection
    st.markdown("---")
    
    if current_x != 0.0 or current_y != 0.0:
        st.success(f"**Selected Coordinates: X = {current_x:.1f}, Y = {current_y:.1f}**")
        
        # Show quadrant information
        if current_x > 0 and current_y > 0:
            quadrant = "Positive & Intensive"
            color = "green"
            description = "High positivity with strong emotional intensity"
        elif current_x < 0 and current_y > 0:
            quadrant = "Negative & Intensive"
            color = "orange"
            description = "High negativity with strong emotional intensity"
        elif current_x < 0 and current_y < 0:
            quadrant = "Negative & Less Intensive"
            color = "blue"
            description = "Negative sentiment with mild emotional intensity"
        elif current_x > 0 and current_y < 0:
            quadrant = "Positive & Less Intensive"
            color = "purple"
            description = "Positive sentiment with mild emotional intensity"
        else:
            quadrant = "On Axis"
            color = "gray"
            description = "Neutral or mixed sentiment"
            
        st.markdown(f"**Sentiment Region:** <span style='color: {color}'>{quadrant}</span>", 
                   unsafe_allow_html=True)
        st.caption(description)
        
        # Reset button
        if st.button("🔄 Reset to Origin"):
            st.session_state.sentiment_x = 0.0
            st.session_state.sentiment_y = 0.0
            st.rerun()
            
    else:
        st.info("**Click on the chart to select coordinates**")
        st.caption("Default position: (0.0, 0.0) - Origin point")
    
    # Instructions
    with st.expander("ℹ️ How to use"):
        st.markdown("""
        **Instructions:**
        1. Click anywhere on the coordinate system to set a point
        2. The coordinates will be automatically rounded to 0.1 precision
        3. Valid range: X and Y from -9.5 to +9.5
        4. The selected point is marked with a red X and blue circle
        5. Use the reset button to return to origin (0,0)
        
        **Coordinate System:**
        - **X-axis**: Negative (left) to Positive (right)
        - **Y-axis**: Less Intensive (bottom) to More Intensive (top)
        
        **Quadrants:**
        - **Top Right**: Positive & Intensive
        - **Top Left**: Negative & Intensive  
        - **Bottom Left**: Negative & Less Intensive
        - **Bottom Right**: Positive & Less Intensive
        """)
    
    # Display session state for debugging (optional)
    if st.checkbox("Show session state (debug)"):
        st.json({
            "sentiment_x": st.session_state.sentiment_x,
            "sentiment_y": st.session_state.sentiment_y
        })

if __name__ == "__main__":
    main()