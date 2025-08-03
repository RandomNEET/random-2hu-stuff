#!/usr/bin/env python3
"""
CSV视频链接规整脚本
标准化YouTube、NicoNico、Bilibili链接格式
"""

import csv
import re
import sys
from urllib.parse import urlparse, parse_qs

def clean_youtube_url(url):
    """将YouTube链接标准化为 https://www.youtube.com/watch?v=VIDEO_ID 格式"""
    if not url or 'youtube.com' not in url and 'youtu.be' not in url:
        return url
    
    # 提取视频ID的正则表达式
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
    """将niconico链接或ID标准化为 https://www.nicovideo.jp/watch/smXXXXX 格式"""
    if not url_or_id:
        return url_or_id
    
    # 如果已经是完整URL
    if url_or_id.startswith('http'):
        if 'nicovideo.jp' in url_or_id:
            # 提取视频ID
            match = re.search(r'/watch/([a-z]{2}[0-9]+)', url_or_id)
            if match:
                video_id = match.group(1)
                return f"https://www.nicovideo.jp/watch/{video_id}"
        return url_or_id
    
    # 如果只是sm号码
    if re.match(r'^[a-z]{2}[0-9]+$', url_or_id):
        return f"https://www.nicovideo.jp/watch/{url_or_id}"
    
    return url_or_id

def clean_bilibili_url(url):
    """将bilibili链接标准化"""
    if not url or 'bilibili.com' not in url:
        return url
    
    # 清理尾部斜杠和参数
    url = url.split('?')[0].rstrip('/')
    
    # 提取av号
    av_match = re.search(r'/video/av([0-9]+)', url)
    if av_match:
        av_id = av_match.group(1)
        return f"https://www.bilibili.com/video/av{av_id}"
    
    # 提取BV号
    bv_match = re.search(r'/video/(BV[a-zA-Z0-9]+)', url)
    if bv_match:
        bv_id = bv_match.group(1)
        return f"https://www.bilibili.com/video/{bv_id}"
    
    return url

def clean_url(url):
    """根据URL类型选择相应的清理函数"""
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
    """处理CSV文件"""
    processed_rows = []
    empty_lines_removed = 0
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            # 读取所有行，手动处理CSV解析以处理复杂情况
            lines = f.readlines()
            
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
                
            # 简单的CSV解析，处理逗号分隔
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
            
            # 确保有足够的列
            while len(parts) < 6:
                parts.append('')
            
            # 清理第二列（原视频链接）和第四列（转载链接）
            if len(parts) > 1:
                parts[1] = clean_url(parts[1])
            if len(parts) > 3:
                parts[3] = clean_url(parts[3])
            
            # 检查是否为空行（所有字段都为空或只有逗号）
            is_empty_row = all(part.strip() == '' for part in parts)
            
            # 跳过空行
            if is_empty_row:
                empty_lines_removed += 1
                continue
            
            # 保存处理后的行
            processed_rows.append(parts)
            
            if line_num <= 5 or line_num % 50 == 0:
                print(f"处理第 {line_num} 行: {parts[0][:30]}...")
    
    except Exception as e:
        print(f"读取文件时出错: {e}")
        return False
    
    # 写入处理后的文件
    try:
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            for row in processed_rows:
                writer.writerow(row)
        
        print(f"\n处理完成！")
        print(f"输入文件: {input_file}")
        print(f"输出文件: {output_file}")
        print(f"处理了 {len(processed_rows)} 行数据")
        print(f"删除了 {empty_lines_removed} 行空行")
        return True
        
    except Exception as e:
        print(f"写入文件时出错: {e}")
        return False

def main():
    if len(sys.argv) != 3:
        print("使用方法: python3 csv_cleaner.py <输入文件> <输出文件>")
        print("示例: python3 csv_cleaner.py input.csv output.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    print("开始处理CSV文件...")
    print("链接标准化规则:")
    print("- YouTube: https://www.youtube.com/watch?v=VIDEO_ID")
    print("- NicoNico: https://www.nicovideo.jp/watch/smXXXXX")
    print("- Bilibili: https://www.bilibili.com/video/avXXXXX 或 https://www.bilibili.com/video/BVXXXXX")
    print()
    
    success = process_csv(input_file, output_file)
    
    if success:
        print("\n处理成功完成！")
    else:
        print("\n处理失败！")
        sys.exit(1)

if __name__ == "__main__":
    main()
