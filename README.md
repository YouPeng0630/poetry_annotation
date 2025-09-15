# Poetry Annotation Tool

A Streamlit-based application for qualitative coding of poems from Poets.org.

## Project Structure

```
poetry_annotation/
├── app.py                 # Main Streamlit application
├── src/                   # Source code modules
│   ├── __init__.py       # Package initialization
│   ├── models.py         # Data models (PoemMeta, PoemText, CodingRecord)
│   ├── scraper.py        # Web scraping and HTML parsing
│   ├── storage.py        # Data storage and retrieval
│   └── utils.py          # Utility functions
├── coding_records/        # Generated data files
│   ├── codings.jsonl     # JSONL log of all coding records
│   └── codings.csv       # CSV snapshot of coding records
├── poets.csv             # Input CSV with poem URLs and metadata
└── requirements.txt      # Python dependencies
```

## Features

- **Interactive Coding Interface**: Tag selection, mood annotation, sentiment coordinates
- **Automatic Data Management**: JSONL logging with CSV snapshots
- **Progress Tracking**: Per-coder progress and statistics
- **Customizable Layout**: Adjustable column width ratios
- **Smart Navigation**: Auto-advance and coder-specific positioning
- **Complete State Management**: UI reset after saving

## Quick Start (Windows)

### One-Click Setup and Run
Double-click `poetry_tool.bat` and choose from the menu:

1. **Quick Start** - Install dependencies and run application
2. **Install Dependencies Only** - Install packages to system Python
3. **Run Application** - Start the app (if dependencies installed)
4. **Run Application (Alternative)** - Alternative run method
5. **Clean Cache and Restart** - Clean temporary files
6. **Exit** - Close the tool

## Manual Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   streamlit run app.py
   ```

## Batch File

- `poetry_tool.bat` - Unified tool with menu options for all operations

## Usage

1. Enter your Coder ID in the sidebar
2. Navigate through poems using the controls
3. Select relevant tags and moods
4. Set sentiment coordinates by clicking on the chart
5. Add notes if needed
6. Save to automatically advance to the next poem

The application automatically tracks your progress and allows you to resume where you left off.
