-- 重新整理videos表的ID，使其连续递增
-- 备份当前数据到临时表

-- 创建临时表存储当前数据
CREATE TEMPORARY TABLE videos_backup AS 
SELECT * FROM videos ORDER BY id;

-- 清空现有表
DELETE FROM videos;

-- 重置自增序列
DELETE FROM sqlite_sequence WHERE name='videos';

-- 按原有顺序重新插入数据，让ID自动递增
INSERT INTO videos (author, original_name, original_url, date, repost_name, repost_url, translation_status)
SELECT author, original_name, original_url, date, repost_name, repost_url, translation_status
FROM videos_backup
ORDER BY id;

-- 删除临时表
DROP TABLE videos_backup;

-- 显示结果统计
SELECT 'Total videos:' as info, COUNT(*) as count FROM videos
UNION ALL
SELECT 'Min ID:', MIN(id) FROM videos
UNION ALL  
SELECT 'Max ID:', MAX(id) FROM videos;
