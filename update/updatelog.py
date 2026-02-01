#!/usr/bin/env python3
"""
Update Log Generator Script

This script generates update log entries for the announcement page by:
1. Reading current database statistics (authors, videos, translated videos)
2. Comparing with the last recorded statistics in content.log
3. Generating update entry for AnnounceView.vue if there are changes
4. Updating content.log with new statistics

Usage:
python3 updatelog.py [--db-path DATABASE_PATH] [--dry-run]

Options:
--db-path: Path to the SQLite database (default: ../backend/random-2hu-stuff.db)
--dry-run: Show what would be updated without making changes
"""

import argparse
import os
import re
import sqlite3
import sys
from datetime import datetime


def create_connection(db_path):
    """Create database connection"""
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None


def get_current_stats(conn):
    """Get current database statistics (same query as /api/stats endpoint)"""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            COUNT(DISTINCT a.id) as totalAuthors,
            COUNT(v.id) as totalVideos,
            COUNT(CASE WHEN v.translation_status IN (1, 2) THEN 1 END) as translatedVideos
        FROM authors a
        LEFT JOIN videos v ON a.id = v.author
    """
    )

    result = cursor.fetchone()
    if result:
        return {
            "totalAuthors": result[0],
            "totalVideos": result[1],
            "translatedVideos": result[2],
        }
    return None


def read_last_stats(content_log_path):
    """Read the last statistics from content.log"""
    if not os.path.exists(content_log_path):
        print(f"Content log file not found: {content_log_path}")
        return None

    try:
        with open(content_log_path, "r") as f:
            lines = f.readlines()
            if lines:
                last_line = lines[-1].strip()
                parts = last_line.split(",")
                if len(parts) == 3:
                    return {
                        "totalAuthors": int(parts[0]),
                        "totalVideos": int(parts[1]),
                        "translatedVideos": int(parts[2]),
                    }
    except Exception as e:
        print(f"Error reading content.log: {e}")

    return None


def update_content_log(content_log_path, stats):
    """Update content.log with new statistics"""
    try:
        # Check if file exists and if the last line ends with newline
        need_newline = False
        if os.path.exists(content_log_path):
            with open(content_log_path, "rb") as f:
                f.seek(-1, 2)  # Go to the last byte
                last_char = f.read(1)
                if last_char != b"\n":
                    need_newline = True

        with open(content_log_path, "a") as f:
            if need_newline:
                f.write("\n")  # Add newline if the last line doesn't end with one
            f.write(
                f"{stats['totalAuthors']},{stats['totalVideos']},{stats['translatedVideos']}\n"
            )
        print(
            f"Updated content.log with new statistics: {stats['totalAuthors']},{stats['totalVideos']},{stats['translatedVideos']}"
        )
    except Exception as e:
        print(f"Error updating content.log: {e}")


def generate_update_entry(author_diff, video_diff, translated_diff):
    """Generate the update entry HTML"""
    today = datetime.now().strftime("%Y.%m.%d")

    # Build the content based on what changed
    content_items = []

    if author_diff > 0 and video_diff > 0 and translated_diff > 0:
        content_items.append(
            f"新收录作者{author_diff}位，视频{video_diff}个，熟肉{translated_diff}个"
        )
    else:
        # Handle individual components
        parts = []
        if author_diff > 0:
            parts.append(f"作者{author_diff}位")
        if video_diff > 0:
            parts.append(f"视频{video_diff}个")
        if translated_diff > 0:
            parts.append(f"熟肉{translated_diff}个")

        if parts:
            content_items.append("新收录" + "，".join(parts))

    if not content_items:
        return None

    # Generate the HTML structure
    html = f"""          <div class="update-item">
            <div class="update-date">{today}</div>
            <div class="update-content">
              <ul>
                <li>{content_items[0]}</li>
              </ul>
            </div>
          </div>

"""

    return html


def update_announcement(vue_file_path, update_entry):
    """Update the AnnounceView.vue file with the new entry"""
    try:
        with open(vue_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find the position to insert the new update entry
        # Look for the first existing update-item and insert before it
        pattern = r'(\s*<div class="update-timeline">\s*\n)'
        match = re.search(pattern, content)

        if match:
            # Insert the new entry right after the update-timeline opening tag
            insert_pos = match.end()
            new_content = content[:insert_pos] + update_entry + content[insert_pos:]

            with open(vue_file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            print(f"Successfully updated {vue_file_path}")
            return True
        else:
            print("Could not find insertion point in AnnounceView.vue")
            return False

    except Exception as e:
        print(f"Error updating AnnounceView.vue: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate update log entries")
    parser.add_argument(
        "--db-path",
        default="../backend/random-2hu-stuff.db",
        help="Path to the SQLite database",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes",
    )

    args = parser.parse_args()

    # Get absolute paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, args.db_path)
    content_log_path = os.path.join(script_dir, "content.log")
    vue_file_path = os.path.join(script_dir, "../frontend/src/views/AnnounceView.vue")

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        sys.exit(1)

    # Connect to database
    conn = create_connection(db_path)
    if not conn:
        sys.exit(1)

    try:
        # Get current statistics
        current_stats = get_current_stats(conn)
        if not current_stats:
            print("Failed to get current statistics")
            sys.exit(1)

        print(
            f"Current stats: Authors={current_stats['totalAuthors']}, Videos={current_stats['totalVideos']}, Translated={current_stats['translatedVideos']}"
        )

        # Get last recorded statistics
        last_stats = read_last_stats(content_log_path)
        if not last_stats:
            print("No previous statistics found in content.log")
            print("Creating initial entry...")
            last_stats = {"totalAuthors": 0, "totalVideos": 0, "translatedVideos": 0}

        print(
            f"Last stats: Authors={last_stats['totalAuthors']}, Videos={last_stats['totalVideos']}, Translated={last_stats['translatedVideos']}"
        )

        # Calculate differences
        author_diff = current_stats["totalAuthors"] - last_stats["totalAuthors"]
        video_diff = current_stats["totalVideos"] - last_stats["totalVideos"]
        translated_diff = (
            current_stats["translatedVideos"] - last_stats["translatedVideos"]
        )

        print(
            f"Differences: Authors=+{author_diff}, Videos=+{video_diff}, Translated=+{translated_diff}"
        )

        # Check if there are any positive changes
        if author_diff <= 0 and video_diff <= 0 and translated_diff <= 0:
            print("No positive changes detected. No update entry needed.")
            return

        # Generate update entry
        update_entry = generate_update_entry(author_diff, video_diff, translated_diff)
        if not update_entry:
            print("No update entry generated.")
            return

        print("\nGenerated update entry:")
        print(update_entry)

        if args.dry_run:
            print("DRY RUN: No files would be modified.")
            return

        # Update AnnounceView.vue
        if update_announcement(vue_file_path, update_entry):
            # Update content.log only if vue update was successful
            update_content_log(content_log_path, current_stats)
            print("Update log generation completed successfully!")
        else:
            print("Failed to update AnnounceView.vue")
            sys.exit(1)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
