"""Local storage functionality for coding records."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import pandas as pd

from models import CodingRecord


def ensure_coding_dir() -> Path:
    """Ensure coding_records directory exists and return path."""
    coding_dir = Path("coding_records")
    coding_dir.mkdir(exist_ok=True)
    return coding_dir


def save_record(record: CodingRecord) -> None:
    """
    Save a coding record to both JSONL log and CSV snapshot.
    
    Args:
        record: The coding record to save
    """
    coding_dir = ensure_coding_dir()
    
    # Append to JSONL log
    jsonl_path = coding_dir / "codings.jsonl"
    record_dict = {
        'timestamp_iso': record.timestamp_iso,
        'coder_id': record.coder_id,
        'url': record.url,
        'poem_uuid': record.poem_uuid,
        'title': record.title,
        'author': record.author,
        'tags': record.tags,
        'moods': record.moods,
        'sentiment_x': record.sentiment_x,
        'sentiment_y': record.sentiment_y,
        'notes': record.notes,
        'is_complete': record.is_complete,
        'html_sha1': record.html_sha1,
        'extraction_ok': record.extraction_ok,
        'error': record.error,
        # Keep sentiment for backward compatibility
        'sentiment': getattr(record, 'sentiment', None),
    }
    
    with open(jsonl_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record_dict, ensure_ascii=False) + '\n')
    
    # Regenerate CSV snapshot from all JSONL records
    update_csv_snapshot()


def update_csv_snapshot() -> None:
    """Update the CSV snapshot from all JSONL records."""
    coding_dir = ensure_coding_dir()
    jsonl_path = coding_dir / "codings.jsonl"
    csv_path = coding_dir / "codings.csv"
    
    if not jsonl_path.exists():
        return
    
    # Read all JSONL records
    records = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    record = json.loads(line)
                    # Join tags and moods for CSV
                    record['tags_joined'] = '; '.join(record.get('tags', []))
                    record['moods_joined'] = '; '.join(record.get('moods', []))
                    records.append(record)
                except json.JSONDecodeError:
                    continue
    
    if records:
        # Create DataFrame and save as CSV
        df = pd.DataFrame(records)
        # Ensure proper column order
        columns = [
            'timestamp_iso', 'coder_id', 'url', 'poem_uuid', 'title', 'author',
            'tags_joined', 'moods_joined', 'sentiment', 'sentiment_x', 'sentiment_y', 'notes', 
            'is_complete', 'html_sha1', 'extraction_ok', 'error'
        ]
        # Only include columns that exist in the data
        available_columns = [col for col in columns if col in df.columns]
        df = df[available_columns]
        
        df.to_csv(csv_path, index=False, encoding='utf-8')


def latest_record_for(url: str) -> Optional[CodingRecord]:
    """
    Get the latest coding record for a specific URL.
    
    Args:
        url: The URL to search for
        
    Returns:
        Latest CodingRecord for the URL, or None if not found
    """
    coding_dir = ensure_coding_dir()
    jsonl_path = coding_dir / "codings.jsonl"
    
    if not jsonl_path.exists():
        return None
    
    latest_record = None
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    record_dict = json.loads(line)
                    if record_dict.get('url') == url:
                        latest_record = CodingRecord(
                            timestamp_iso=record_dict['timestamp_iso'],
                            coder_id=record_dict['coder_id'],
                            url=record_dict['url'],
                            poem_uuid=record_dict.get('poem_uuid'),
                            title=record_dict.get('title'),
                            author=record_dict.get('author'),
                            tags=record_dict.get('tags', []),
                            moods=record_dict.get('moods', []),
                            sentiment_x=record_dict.get('sentiment_x', 0.0),
                            sentiment_y=record_dict.get('sentiment_y', 0.0),
                            notes=record_dict.get('notes', ''),
                            is_complete=record_dict.get('is_complete', False),
                            html_sha1=record_dict.get('html_sha1', ''),
                            extraction_ok=record_dict.get('extraction_ok', True),
                            error=record_dict.get('error'),
                            sentiment=record_dict.get('sentiment'),  # Keep for backward compatibility
                        )
                except json.JSONDecodeError:
                    continue
    
    return latest_record


def get_coding_stats() -> dict:
    """Get statistics about coding progress."""
    coding_dir = ensure_coding_dir()
    jsonl_path = coding_dir / "codings.jsonl"
    
    if not jsonl_path.exists():
        return {'total_records': 0, 'completed_records': 0, 'unique_urls': 0}
    
    urls_seen = set()
    completed_urls = set()
    total_records = 0
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    record = json.loads(line)
                    url = record.get('url')
                    if url:
                        urls_seen.add(url)
                        if record.get('is_complete', False):
                            completed_urls.add(url)
                        total_records += 1
                except json.JSONDecodeError:
                    continue
    
    return {
        'total_records': total_records,
        'completed_records': len(completed_urls),
        'unique_urls': len(urls_seen),
    }
