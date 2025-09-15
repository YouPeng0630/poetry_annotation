# Poetry Annotation Tool

A Streamlit-based application for qualitative coding of poems from Poets.org (Test version).

## Quick Start (Windows)

Double-click `poetry_tool.bat` and choose:

1. **Install and Run** - Install dependencies and start application
2. **Run Application** - Start the app directly

## Mac Version
###First Step: Install the dependencies with:

```bash
pip install -r requirements.txt

###Second Step: Run the app

```bash
streamlit run src/app.py

## Batch File

- `poetry_tool.bat` - Simple tool with two options for setup and running

## Usage

1. Enter your Coder ID in the sidebar
2. Navigate through poems using the controls
3. Select relevant tags and moods
4. Set sentiment coordinates by clicking on the chart
5. Add notes if needed
6. Click *save* button to automatically go to the next poem

The application automatically tracks your progress and allows you to resume where you left off (By entering your Coder ID in the sidebar).
