# Qualitative Coding for Poets.org

A local-only Streamlit application for qualitative coding of poems from Poets.org. This tool allows researchers to systematically analyze and code poems with tags, sentiment analysis, and detailed notes.

## Features

- 🔍 **Web Scraping**: Fetches poem content from Poets.org with intelligent caching
- 🏷️ **Flexible Tagging**: Customizable tag system with base tags and freeform input
- 📊 **Sentiment Analysis**: Rate poems as positive, neutral, negative, or unsure
- 📝 **Note Taking**: Rich text notes for qualitative observations
- 💾 **Local Storage**: All data stored locally in JSONL and CSV formats
- 🔄 **Progress Tracking**: Visual progress indicators and navigation
- 🚀 **No Database Required**: File-based storage for simplicity

## Setup & Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Installation

1. Clone or download this repository
2. Navigate to the project directory
3. Install dependencies:

```bash
pip install -r requirements.txt
```

### Running the Application

```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`.

## Usage

### 1. Prepare Your Data

Create a CSV file named `poets.csv` (or upload via the interface) with poem URLs. The CSV should have one of these column headers:
- `url`
- `URL` 
- `link`
- `href`

Example `poets.csv`:
```csv
url,title,author
https://poets.org/poem/line-storm-song,Line-Storm Song,Robert Frost
https://poets.org/poem/stopping-woods-snowy-evening,Stopping by Woods on a Snowy Evening,Robert Frost
```

### 2. Configure Coding Settings

- **Coder ID**: Enter your unique identifier for tracking your coding work
- **Base Tags**: Customize the available tags for consistent coding
- **CSV Source**: Upload a file or specify the path to your `poets.csv`

### 3. Code Poems

For each poem, you can:
- **Select Tags**: Choose from your base tag set
- **Add Custom Tags**: Enter additional tags separated by commas
- **Rate Sentiment**: Choose positive, neutral, negative, or unsure
- **Write Notes**: Add detailed qualitative observations
- **Mark Complete**: Indicate when you've finished coding a poem

### 4. Navigate and Track Progress

- Use **Prev/Next** buttons to navigate between poems
- **Skip** to move forward without coding
- **Reload** to refresh the current poem
- **Open Source Page** to view the original on Poets.org
- Monitor your progress in the sidebar

## Data Storage

All coding data is stored locally in the `coding_records/` directory:

### Files Created

- **`codings.jsonl`**: Append-only log of all coding records (one JSON object per line)
- **`codings.csv`**: Latest snapshot of all codings in CSV format for analysis

### Data Schema

Each coding record contains:
- `timestamp_iso`: When the coding was created
- `coder_id`: Your coder identifier
- `url`: Original poem URL
- `poem_uuid`: Poets.org internal poem ID (if available)
- `title`: Poem title
- `author`: Poem author
- `tags_joined`: All tags separated by semicolons
- `sentiment`: Sentiment rating
- `notes`: Your qualitative notes
- `is_complete`: Whether coding is marked complete
- `html_sha1`: Hash of cached HTML for traceability
- `extraction_ok`: Whether poem extraction succeeded
- `error`: Any extraction errors

## Caching

HTML content is cached in the `html_cache/` directory to:
- Speed up repeated access to the same poems
- Allow offline work after initial fetch
- Reduce load on Poets.org servers

Cache files are named using URL slugs and stored as `.html` files.

## Poem Data Extraction

The application extracts the following metadata from each poem page:

### Primary Content
- **Title**: Main poem title
- **Author**: Author name and profile link
- **Poem Text**: Full poem with preserved line breaks and stanza structure
- **Themes**: Associated themes/topics
- **Publication Info**: Date published and modified

### Additional Metadata
- **Canonical URL**: Official poem URL
- **Poem UUID**: Internal Poets.org identifier
- **About Section**: Editorial notes about the poem
- **Public Domain Status**: Copyright information

### Text Preservation
The application carefully preserves:
- Original line breaks within stanzas
- Stanza separations (blank lines between paragraphs)
- Long-line formatting
- Special characters and punctuation

## Legal and Ethical Considerations

⚖️ **Important**: This tool is designed for academic research and educational purposes only.

- **Respect Terms of Service**: Always comply with Poets.org's terms of service
- **Rate Limiting**: Built-in delays prevent overwhelming the server
- **Research Use**: Do not mass-redistribute scraped content
- **Attribution**: Always credit original sources in your research

## Technical Details

### Architecture
- **Frontend**: Streamlit web interface
- **Scraping**: requests + BeautifulSoup with intelligent parsing
- **Storage**: JSON Lines + CSV for maximum compatibility
- **Caching**: File-based HTML caching with fallback support

### Error Handling
- Graceful handling of network failures
- Fallback to cached content when possible
- Clear error messages for debugging
- Continued operation even with failed extractions

### Performance
- Exponential backoff for rate limiting
- Efficient HTML parsing with targeted selectors
- Minimal memory footprint with streaming JSONL

## Troubleshooting

### Common Issues

**"No valid URLs found in CSV"**
- Check that your CSV has a column named `url`, `URL`, `link`, or `href`
- Ensure URLs are not empty and properly formatted

**"Error loading poem"**
- Check your internet connection
- The poem may have been moved or removed from Poets.org
- Try the "Reload" button or skip to the next poem

**"Error saving coding"**
- Ensure you have write permissions in the project directory
- Check that the `coding_records/` directory can be created

**Slow performance**
- Large CSV files may take time to process initially
- Network issues can slow down poem fetching
- Consider coding in smaller batches

### Getting Help

If you encounter issues:
1. Check the error messages in the Streamlit interface
2. Look for error details in the terminal/console
3. Verify your CSV format matches the expected schema
4. Ensure all dependencies are properly installed

## File Structure

```
.
├── app.py                    # Main Streamlit application
├── scraper.py               # HTML fetching and parsing
├── storage.py               # Local data storage
├── models.py                # Data model definitions
├── utils.py                 # Utility functions
├── requirements.txt         # Python dependencies
├── README.md               # This file
├── poets.csv               # Your poem URLs (create this)
├── html_cache/             # Cached HTML files (auto-created)
└── coding_records/         # Coding outputs (auto-created)
    ├── codings.jsonl       # Append-only log
    └── codings.csv         # Latest snapshot
```

## Contributing

This is a research tool designed for academic use. Feel free to modify and extend it for your specific research needs.

## License

This tool is provided for educational and research purposes. Please respect the terms of service of any websites you scrape and always attribute original sources in your research.

