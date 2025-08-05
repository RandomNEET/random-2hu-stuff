#!/usr/bin/env python3
"""
CSV Video Link Standardization Script
Standardize YouTube, NicoNico, Bilibili link formats
"""

import csv
import re
import sys
from urllib.parse import urlparse, parse_qs

def clean_youtube_url(url):
    """Standardize YouTube links to https://www.youtube.com/watch?v=VIDEO_ID format"""
    if not url or 'youtube.com' not in url and 'youtu.be' not in url:
        return url
    
    # Regular expressions to extract video ID
    patterns = [
        r'(?:youtube\.com/watch\?v=)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'(?:youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com/v/)([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            return f"https://www.youtube.com/watch?v={video_id}"
    
    return url

def clean_niconico_url(url_or_id):
    """Standardize niconico links or IDs to https://www.nicovideo.jp/watch/smXXXXX format"""
    if not url_or_id:
        return url_or_id
    
    # If already a complete URL
    if url_or_id.startswith('http'):
        if 'nicovideo.jp' in url_or_id:
            # Extract video ID
            match = re.search(r'/watch/([a-z]{2}[0-9]+)', url_or_id)
            if match:
                video_id = match.group(1)
                return f"https://www.nicovideo.jp/watch/{video_id}"
        return url_or_id
    
    # If only sm number
    if re.match(r'^[a-z]{2}[0-9]+$', url_or_id):
        return f"https://www.nicovideo.jp/watch/{url_or_id}"
    
    return url_or_id

def clean_bilibili_url(url):
    """Standardize bilibili links"""
    if not url or 'bilibili.com' not in url:
        return url
    
    # Clean trailing slashes and parameters
    url = url.split('?')[0].rstrip('/')
    
    # Extract av number
    av_match = re.search(r'/video/av([0-9]+)', url)
    if av_match:
        av_id = av_match.group(1)
        return f"https://www.bilibili.com/video/av{av_id}"
    
    # Extract BV number
    bv_match = re.search(r'/video/(BV[a-zA-Z0-9]+)', url)
    if bv_match:
        bv_id = bv_match.group(1)
        return f"https://www.bilibili.com/video/{bv_id}"
    
    return url

def clean_url(url):
    """Select appropriate cleaning function based on URL type"""
    if not url or url.strip() == '':
        return url
    
    url = url.strip()
    
    # YouTube
    if 'youtube.com' in url or 'youtu.be' in url:
        return clean_youtube_url(url)
    
    # NicoNico
    if 'nicovideo.jp' in url or re.match(r'^[a-z]{2}[0-9]+$', url):
        return clean_niconico_url(url)
    
    # Bilibili
    if 'bilibili.com' in url:
        return clean_bilibili_url(url)
    
    return url

def process_csv(input_file, output_file):
    """Process CSV file"""
    processed_rows = []
    empty_lines_removed = 0
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            # Read all lines, manually handle CSV parsing for complex cases
            lines = f.readlines()
            
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
                
            # Simple CSV parsing, handle comma separation
            parts = []
            current_part = ""
            in_quotes = False
            
            i = 0
            while i < len(line):
                char = line[i]
                if char == '"':
                    in_quotes = not in_quotes
                elif char == ',' and not in_quotes:
                    parts.append(current_part.strip())
                    current_part = ""
                    i += 1
                    continue
                current_part += char
                i += 1
            
            parts.append(current_part.strip())
            
            # Ensure enough columns
            while len(parts) < 7:
                parts.append('')
            
            # Clean second column (original video link) and fourth column (repost link)
            if len(parts) > 1:
                parts[1] = clean_url(parts[1])
            if len(parts) > 3:
                parts[3] = clean_url(parts[3])
            
            # Check if empty row (all fields are empty or only commas)
            is_empty_row = all(part.strip() == '' for part in parts)
            
            # Skip empty rows
            if is_empty_row:
                empty_lines_removed += 1
                continue
            
            # Save processed row
            processed_rows.append(parts)
            
            if line_num <= 5 or line_num % 50 == 0:
                print(f"Processing line {line_num}: {parts[0][:30]}...")
    
    except Exception as e:
        print(f"Error reading file: {e}")
        return False
    
    # Write processed file
    try:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            for row in processed_rows:
                writer.writerow(row)
        
        print(f"\nProcessing completed!")
        print(f"Input file: {input_file}")
        print(f"Output file: {output_file}")
        print(f"Processed {len(processed_rows)} rows of data")
        print(f"Removed {empty_lines_removed} empty rows")
        return True
        
    except Exception as e:
        print(f"Error writing file: {e}")
        return False

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 csv_cleaner.py <input_file> <output_file>")
        print("Example: python3 csv_cleaner.py input.csv output.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    print("Starting CSV file processing...")
    print("Link standardization rules:")
    print("- YouTube: https://www.youtube.com/watch?v=VIDEO_ID")
    print("- NicoNico: https://www.nicovideo.jp/watch/smXXXXX")
    print("- Bilibili: https://www.bilibili.com/video/avXXXXX or https://www.bilibili.com/video/BVXXXXX")
    print()
    
    success = process_csv(input_file, output_file)
    
    if success:
        print("\nProcessing completed successfully!")
    else:
        print("\nProcessing failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
