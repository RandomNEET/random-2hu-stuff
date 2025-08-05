-- Reorganize video table IDs to make them consecutive and incremental
-- Backup current data to temporary table

-- Create temporary table to store current data
CREATE TEMPORARY TABLE videos_backup AS 
SELECT * FROM videos ORDER BY id;

-- Clear existing table
DELETE FROM videos;

-- Reset auto-increment sequence
DELETE FROM sqlite_sequence WHERE name='videos';

-- Reinsert data in original order, allowing IDs to auto-increment
INSERT INTO videos (author, original_name, original_url, original_thumbnail, date, repost_name, repost_url, repost_thumbnail, translation_status, comment)
SELECT author, original_name, original_url, original_thumbnail, date, repost_name, repost_url, repost_thumbnail, translation_status, comment
FROM videos_backup
ORDER BY id;

-- Drop temporary table
DROP TABLE videos_backup;

-- Show result statistics
SELECT 'Total videos:' as info, COUNT(*) as count FROM videos
UNION ALL
SELECT 'Min ID:', MIN(id) FROM videos
UNION ALL  
SELECT 'Max ID:', MAX(id) FROM videos;
