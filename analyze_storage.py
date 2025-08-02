#!/usr/bin/env python3
"""
Storage Analytics Script for TraceTracks
Analyzes the stored video data and provides statistics.
"""

import os
from collections import defaultdict

def analyze_storage():
    """
    Analyze the stored video data and calculate statistics
    """
    storage_file = 'storage/links_info.txt'
    
    if not os.path.exists(storage_file):
        print("Error: storage/links_info.txt not found!")
        print("Please run the TraceTracks script first to generate data.")
        return
    
    total_views = 0
    total_videos = 0
    channels = set()
    
    # Statistics per channel
    channel_stats = defaultdict(lambda: {'videos': 0, 'views': 0})
    
    try:
        with open(storage_file, 'r', encoding='utf-8') as file:
            content = file.read().strip()
            
            if not content:
                print("Storage file is empty!")
                return
            
            video_blocks = content.split('\n\n')            
            for block in video_blocks:
                if block.strip():
                    lines = block.strip().split('\n')
                    
                    if len(lines) >= 4:
                        try:
                            views = int(lines[1].replace('Views: ', ''))
                            author = lines[2].replace('Author: ', '')
                            
                            total_views += views
                            total_videos += 1
                            channels.add(author)
                            
                            channel_stats[author]['videos'] += 1
                            channel_stats[author]['views'] += views
                            
                        except ValueError as e:
                            print(f"Warning: Could not parse views for block: {block[:50]}...")
                            continue
    
    except FileNotFoundError:
        print("Error: storage/links_info.txt not found!")
        return
    except Exception as e:
        print(f"Error reading storage file: {e}")
        return
    
    # Display overall statistics
    print("="*60)
    print("STORAGE ANALYTICS - OVERALL STATISTICS")
    print("="*60)
    print(f"Total Videos: {total_videos:,}")
    print(f"Total Views: {total_views:,}")
    print(f"Total Different Channels: {len(channels)}")
    print()
    
    # Display top channels by video count
    print("="*60)
    print("TOP CHANNELS BY VIDEO COUNT")
    print("="*60)
    sorted_by_videos = sorted(channel_stats.items(), key=lambda x: x[1]['videos'], reverse=True)
    
    for i, (channel, stats) in enumerate(sorted_by_videos[:10], 1):
        avg_views = stats['views'] / stats['videos'] if stats['videos'] > 0 else 0
        print(f"{i:2}. {channel}")
        print(f"    Videos: {stats['videos']:,} | Total Views: {stats['views']:,} | Avg Views: {avg_views:,.1f}")
        print()
    
    # Display top channels by total views
    print("="*60)
    print("TOP CHANNELS BY TOTAL VIEWS")
    print("="*60)
    sorted_by_views = sorted(channel_stats.items(), key=lambda x: x[1]['views'], reverse=True)
    
    for i, (channel, stats) in enumerate(sorted_by_views[:10], 1):
        avg_views = stats['views'] / stats['videos'] if stats['videos'] > 0 else 0
        print(f"{i:2}. {channel}")
        print(f"    Total Views: {stats['views']:,} | Videos: {stats['videos']:,} | Avg Views: {avg_views:,.1f}")
        print()
    
    # Display view distribution
    print("="*60)
    print("VIEW DISTRIBUTION")
    print("="*60)
    
    # Read all videos to analyze view distribution
    all_views = []
    with open(storage_file, 'r', encoding='utf-8') as file:
        content = file.read().strip()
        video_blocks = content.split('\n\n')
        
        for block in video_blocks:
            if block.strip():
                lines = block.strip().split('\n')
                if len(lines) >= 4:
                    try:
                        views = int(lines[1].replace('Views: ', ''))
                        all_views.append(views)
                    except ValueError:
                        continue
    
    if all_views:
        all_views.sort()
        print(f"Highest Views: {max(all_views):,}")
        
        # View ranges
        ranges = [
            (0, 100, "0-100 views"),
            (101, 1000, "101-1K views"),
            (1001, 10000, "1K-10K views"),
            (10001, 100000, "10K-100K views"),
            (100001, float('inf'), "100K+ views")
        ]
        
        print("\nView Ranges:")
        for min_views, max_views, label in ranges:
            count = sum(1 for v in all_views if min_views <= v <= max_views)
            percentage = (count / len(all_views)) * 100 if all_views else 0
            print(f"  {label}: {count:,} videos ({percentage:.1f}%)")

def main():
    print("TraceTracks - Storage Analytics")
    print("Analyzing stored video data...\n")
    analyze_storage()

if __name__ == '__main__':
    main()
