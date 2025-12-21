-- ========================================================================
-- Video IDs Fix Script for random-2hu-stuff Database
-- ========================================================================
-- Purpose: Reorganize video table IDs to make them consecutive and incremental
-- Warning: This script will modify the database. Make sure to backup first!
-- 
-- Usage: 
-- 1. First create backup: cp random-2hu-stuff.db random-2hu-stuff.db.bak
-- 2. Run this script: sqlite3 random-2hu-stuff.db < fix_video_ids.sql
-- ========================================================================

-- Enable foreign key constraints (if any exist)
PRAGMA foreign_keys = ON;

-- Start transaction for atomicity
BEGIN TRANSACTION;

-- Check current state before modification
.print "=== BEFORE MODIFICATION ==="
SELECT 'Total videos: ' || COUNT(*) FROM videos;
SELECT 'ID range: ' || MIN(id) || ' - ' || MAX(id) FROM videos;

-- Check for gaps in ID sequence
WITH RECURSIVE gaps AS (
    SELECT 1 as expected_id
    UNION ALL
    SELECT expected_id + 1 
    FROM gaps 
    WHERE expected_id < (SELECT MAX(id) FROM videos)
)
SELECT 'Missing IDs: ' || COUNT(*) 
FROM gaps 
WHERE expected_id NOT IN (SELECT id FROM videos);

-- Create temporary table to store current data with proper column order
CREATE TEMPORARY TABLE videos_backup AS 
SELECT id, author, original_name, original_url, original_thumbnail, 
       date, repost_name, repost_url, repost_thumbnail, 
       translation_status, comment
FROM videos 
ORDER BY id;

-- Verify backup was created successfully
SELECT 'Backup created with ' || COUNT(*) || ' records' FROM videos_backup;

-- Clear existing table
DELETE FROM videos;

-- Reset auto-increment sequence to start from 1
DELETE FROM sqlite_sequence WHERE name='videos';
INSERT OR REPLACE INTO sqlite_sequence (name, seq) VALUES ('videos', 0);

-- Reinsert data in original order, allowing IDs to auto-increment consecutively
INSERT INTO videos (author, original_name, original_url, original_thumbnail, 
                   date, repost_name, repost_url, repost_thumbnail, 
                   translation_status, comment)
SELECT author, original_name, original_url, original_thumbnail, 
       date, repost_name, repost_url, repost_thumbnail, 
       translation_status, comment
FROM videos_backup
ORDER BY id;

-- Verify the reorganization was successful
.print "=== AFTER MODIFICATION ==="
SELECT 'Total videos: ' || COUNT(*) FROM videos;
SELECT 'ID range: ' || MIN(id) || ' - ' || MAX(id) FROM videos;

-- Final verification: check if IDs are now consecutive
WITH RECURSIVE expected_sequence AS (
    SELECT 1 as expected_id
    UNION ALL
    SELECT expected_id + 1 
    FROM expected_sequence 
    WHERE expected_id < (SELECT MAX(id) FROM videos)
)
SELECT 'IDs are consecutive: ' || 
       CASE 
           WHEN COUNT(*) = 0 THEN 'YES' 
           ELSE 'NO - ' || COUNT(*) || ' gaps found'
       END as status
FROM expected_sequence 
WHERE expected_id NOT IN (SELECT id FROM videos);

-- Drop temporary table
DROP TABLE videos_backup;

-- Commit transaction
COMMIT;

.print "=== OPERATION COMPLETED ==="
.print "Database reorganization finished successfully!"
.print "All video IDs are now consecutive starting from 1."
