from googleapiclient.discovery import build
import requests
import re
import os
import argparse

# --- API ---
youtube_api_key = open('youtube_api.key', encoding='utf-8').read()
if not youtube_api_key.strip():
    print("Error: youtube_api.key file is empty or not found!")
    print("Please fill in the youtube_api.key file with your YouTube API key.")
    exit(1)
youtube = build('youtube', 'v3', developerKey=youtube_api_key)
# Must be signed to a SoundCloud account to get the client_id.
# You can get it from the browser's developer tools, in the Network tab, when you load a SoundCloud page.
# And then, look at the different requests and try to find one that has a "client_id" parameter in the URL.

# --- Single Key Input ---
def get_single_key():
    """Get a single key press without requiring Enter - cross-platform"""
    import sys
    import os
    
    if os.name == 'nt':  # Windows
        try:
            import msvcrt
            print("", end='', flush=True)
            while True:
                ch = msvcrt.getch().decode('utf-8').lower()
                if ch == '\x03':
                    raise KeyboardInterrupt
                elif ch in ['y', 'n', '\r', '\n', ' ']:
                    if ch in ['\r', '\n', ' ']:
                        return 'n'
                    return ch
        except Exception:
            response = input().lower().strip()
            return response[0] if response else 'n'
    else:  # Linux/macOS
        try:
            import tty
            import termios
            
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
                if ch == '\x03':
                    raise KeyboardInterrupt
                elif ch == '\x04':
                    return 'n'
                elif ch == '\r' or ch == '\n':
                    return 'n'
                return ch.lower()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except Exception:
            response = input().lower().strip()
            return response[0] if response else 'n'

# --- Clean Title ---
def clean_title(title: str) -> str:
    # Replace Bootleg/Remix with the genre only
    # Example: if the title is "MySong1 [Techno Bootleg]", it'll be "MySong1 Techno"
    title = re.sub(r'\((.*?)Bootleg\)', r'\1', title)  # Replace "(Genre Bootleg)" with "Genre"
    title = re.sub(r'\[(.*?)Bootleg\]', r'\1', title)  # Replace "[Genre Bootleg]" with "Genre"
    title = re.sub(r'\((.*?)Remix\)', r'\1', title)  # Replace "(Genre Remix)" with "Genre"
    title = re.sub(r'\[(.*?)Remix\]', r'\1', title)  # Replace "[Genre Remix]" with "Genre"

    # doesn't remove: ' and a-zA-Z0-9
    title = re.sub(r'[^\w\s\']', '', title)
    title = re.sub(r'\[.*?\]', '', title)
    title = re.sub(r'\(.*?\)', '', title)

    # remove multiple spaces
    title = re.sub(r'\s+', ' ', title)

    return title.strip()

# --- Search Videos ---
def search_videos(query: str) -> list:
    search_response = youtube.search().list(
        q=query,
        part='id,snippet',
        maxResults=50,
        type='video'
    ).execute()

    videos = []
    for search_result in search_response.get('items', []):
        try:
            video_id = search_result['id']['videoId']
            video_details = youtube.videos().list(
                part='snippet,statistics',
                id=video_id
            ).execute()

            if video_details['items']:
                if query.lower() not in video_details['items'][0]['snippet']['description'].lower():
                    continue
                video_info = video_details['items'][0]
                video_title = video_info['snippet']['title']
                video_views = video_info['statistics']['viewCount']
                video_author = video_info['snippet']['channelTitle']
                video_link = f'https://www.youtube.com/watch?v={video_id}'
                videos.append({
                    'title': video_title,
                    'views': video_views,
                    'author': video_author,
                    'link': video_link
                })
        except:
            pass
    return videos

# --- Get App Version ---
def get_app_version() -> str:
    headers = {
        'User-Agent': 'Mozilla/5.0',
    }
    response = requests.get('https://soundcloud.com/versions.json', headers=headers).json()
    return response['app']

# --- Search by Username ---
def search_by_username(username: str, client_id: str, app_version: str) -> str:
    headers = {
        'User-Agent': 'Mozilla/5.0',
    }

    url = f'https://api-v2.soundcloud.com/search?q={username}&client_id={client_id}&limit=1&app_version={app_version}'

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return None
    
    data = response.json()
    # print(data)
    if 'collection' in data and len(data['collection']) > 0:
        user_id = data['collection'][0]['id']
        return user_id

# --- Get ID from a SoundCloud Link ---
def get_id_from_link(link: str) -> str:
    headers = {
        'User-Agent': 'Mozilla/5.0',
    }

    response = requests.get(link, headers=headers)
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return None
    
    match = re.search(r'soundcloud://users:(\d+)', response.text)
    if match:
        user_id = match.group(1)
        return user_id

# --- Get SoundCloud tracks ---
def get_soundcloud_tracks(user_id: str, client_id: str, app_version: str) -> list:
    headers = {
        'User-Agent': 'Mozilla/5.0',
    }

    params = {
        'representation': '',
        'client_id': client_id,
        'limit': '100',
        'offset': '0',
        'linked_partitioning': '1',
        'app_version': app_version,
        'app_locale': 'en',
    }

    response = requests.get(f'https://api-v2.soundcloud.com/users/{user_id}/tracks', params=params, headers=headers).json()
    tracks = []
    # print(response)
    for track in response['collection']:
        tracks.append({
            'title': clean_title(track['title']),
            'author': track['user']['username'],
            'link': track['permalink_url'][23:],
            'playback_count': track.get('playback_count', 0)
        })
    return tracks[::-1]

# --- Storage Management ---
def load_existing_data():
    video_data = {}
    
    if os.path.exists('storage/links_info.txt'):
        with open('storage/links_info.txt', 'r', encoding='utf-8') as file:
            content = file.read().strip()
            if content:
                video_blocks = content.split('\n\n')
                for block in video_blocks:
                    if block.strip():
                        lines = block.strip().split('\n')
                        if len(lines) >= 4:
                            try:
                                title = lines[0].replace('Title: ', '')
                                views = int(lines[1].replace('Views: ', ''))
                                author = lines[2].replace('Author: ', '')
                                link = lines[3].replace('Link: ', '')
                                video_data[link] = {
                                    'title': title,
                                    'views': views,
                                    'author': author,
                                    'link': link
                                }
                            except ValueError as e:
                                print(f"Warning: Could not parse views for block: {block[:50]}...")
                                continue
    return video_data

def save_video_data(video_data):
    """Save video data to files"""
    os.makedirs('storage', exist_ok=True)
    
    with open('storage/links.txt', 'w', encoding='utf-8') as links_file, \
        open('storage/links_info.txt', 'w', encoding='utf-8') as info_file:
        
        for video in video_data.values():
            links_file.write(video['link'] + '\n')
            info_file.write(f"Title: {video['title']}\nViews: {video['views']}\nAuthor: {video['author']}\nLink: {video['link']}\n\n")

def process_video(video, video_data):
    """Process a single video and update storage if necessary"""
    link = video['link']
    views = int(video['views'])
    
    if link in video_data:
        existing_views = int(video_data[link]['views']) if isinstance(video_data[link]['views'], str) else video_data[link]['views']
        if views > existing_views:
            video_data[link] = video
            video_data[link]['views'] = views
            print(f"Updated views for: {video['title']} ({views} views)")
    else:
        video_data[link] = video
        video_data[link]['views'] = views
        print(f"Added new video: {video['title']} ({views} views)")

# --- Main code ---
# https://serpapi.com/youtube-search-api#api-parameters-advanced-youtube-parameters
# It can also be used for forcing the exact search query spelling by setting the sp value to QgIIAQ%3D%3D.
# ?sp=QgIIAQ%3D%3D

def main(username=None, client_id=None, song=None, all_tracks=False, sort_by="recent", num_tracks=1):
    """
    Main function to search for YouTube videos based on SoundCloud tracks
    
    Args:
        username (str): SoundCloud username or link. If None, will prompt for input
        client_id (str): SoundCloud client ID. If None, will prompt for input
        song (str): Specific song title or link to search for. If provided, only this song will be processed
        all_tracks (bool): If True, list all tracks and ask for each one individually
        sort_by (str): Sorting method - "recent", "oldest", or "popular" (default: "recent")
        num_tracks (int): Number of tracks to process (default: 1)
    """
    
    app_version = get_app_version()
    
    if username is None:
        input_username = input("Enter the SoundCloud username or link: ").strip()
    else:
        input_username = username
        
    if client_id is None:
        input_client_id = input("Enter the SoundCloud client ID: ").strip()
        if not input_client_id:
            print("Error: SoundCloud client ID is required!")
            print("You can get it from the browser's developer tools, in the Network tab, when you load a SoundCloud page.")
            print("Look for requests that have a 'client_id' parameter in the URL.")
            return
    else:
        input_client_id = client_id
        
    if input_username.startswith('https://soundcloud.com/'):
        artist_id = get_id_from_link(input_username)
        print(f"Artist ID from link: {artist_id}")
    else:
        artist_id = search_by_username(input_username, input_client_id, app_version)
        print(f"Artist ID from username: {artist_id}")

    if not artist_id:
        print("Could not find artist ID")
        return

    video_data = load_existing_data()
    print(f"Loaded {len(video_data)} existing videos from storage")

    soundcloud_parsing = get_soundcloud_tracks(artist_id, input_client_id, app_version)
    
    # Filter by specific song if provided
    if song:
        print(f"Searching for specific song: {song}")        
        if song.startswith('https://soundcloud.com/'):
            song_slug = song.split('/')[-1]
            filtered_tracks = [track for track in soundcloud_parsing if song_slug in track['link']]
        else:
            song_lower = song.lower()
            filtered_tracks = [track for track in soundcloud_parsing if song_lower in track['title'].lower()]
        
        if not filtered_tracks:
            print(f"No tracks found matching: {song}")
            print("Available tracks:")
            for track in soundcloud_parsing[::-1]:
                print(f"  - {track['title']} ({track['link']})")
            return
        
        print(f"Found {len(filtered_tracks)} matching track(s)")
        tracks_to_select = filtered_tracks
        
    elif all_tracks:
        print(f"Found {len(soundcloud_parsing)} tracks. Listing all tracks (most recent first):")
        tracks_to_select = soundcloud_parsing[::-1]
        
    else:
        # Apply sorting based on the sort_by parameter (when not using --song or --all)
        if sort_by == "oldest":
            # Keep original order (oldest first)
            tracks_to_process = soundcloud_parsing[:num_tracks]
            print(f"Processing {num_tracks} oldest tracks")
        elif sort_by == "recent":
            # Reverse order for most recent first
            tracks_to_process = soundcloud_parsing[-num_tracks:][::-1]
            print(f"Processing {num_tracks} most recent tracks")
        elif sort_by == "popular":
            # Sort tracks by playback_count in descending order (most popular first)
            sorted_tracks = sorted(soundcloud_parsing, key=lambda x: x['playback_count'], reverse=True)
            tracks_to_process = sorted_tracks[:num_tracks]
            print(f"Processing {num_tracks} most popular tracks")
        else:
            tracks_to_process = soundcloud_parsing[:num_tracks]
            print(f"Invalid sort_by parameter. Using default: {num_tracks} tracks")
    
    # Interactive selection for --song or --all
    if song or all_tracks:
        tracks_to_process = []
        for i, track in enumerate(tracks_to_select, 1):
            print(f"\n{i}. {track['title']} by {track['author']}")
            print(f"   Plays: {track['playback_count']:,}")
            print(f"   Link: soundcloud.com/{track['link']}")
            
            print(f"Search for YouTube videos of this track? (y/n): ", end='', flush=True)
            choice = get_single_key()
            
            print(f"[{choice}]")
            
            if choice == 'y':
                tracks_to_process.append(track)
                print("✓ Added to processing list")
            elif choice == 'n':
                print("✗ Skipped")
            else:
                print(f"✗ Skipped (unrecognized input: '{choice}')")
        
        if not tracks_to_process:
            print("\nNo tracks selected for processing.")
            return
            
        print(f"\nProcessing {len(tracks_to_process)} selected track(s)")
    
    for track in tracks_to_process:
        videos = search_videos(track['title'] + ' ' + track['author'])
        if videos:
            print(f"Found {len(videos)} videos for '{track['title']} {track['author']}':")
            for video in videos:
                print(f"  Title: {video['title']}")
                print(f"  Views: {video['views']}")
                print(f"  Channel: {video['author']}")
                print(f"  Link: {video['link']}")
                print()
                process_video(video, video_data)
        else:
            print(f"No videos found for '{track['title']} {track['author']}'")
        
        videos = search_videos(track['link'])
        if videos:
            print(f"Found {len(videos)} videos for '{track['link']}':")
            for video in videos:
                print(f"  Title: {video['title']}")
                print(f"  Views: {video['views']}")
                print(f"  Channel: {video['author']}")
                print(f"  Link: {video['link']}")
                print()
                process_video(video, video_data)

    save_video_data(video_data)
    print(f"Saved {len(video_data)} videos to storage")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='TraceTracks - Find YouTube videos based on SoundCloud tracks')
    parser.add_argument('--username', '-u', type=str, help='SoundCloud username or profile URL')
    parser.add_argument('--client-id', '-c', type=str, help='SoundCloud client ID (if not provided, will prompt for input)')
    parser.add_argument('--song', '-s', type=str, help='Search for a specific song by title or SoundCloud link')
    parser.add_argument('--all', '-a', action='store_true', help='List all tracks and ask for each one individually')
    parser.add_argument('--sort-by', '-sb', type=str, choices=['recent', 'oldest', 'popular'], 
                       default='recent', help='Sort tracks by: recent, oldest, or popular (default: recent)')
    parser.add_argument('--num-tracks', '-n', type=int, default=1, 
                       help='Number of tracks to process (default: 1)')
    
    args = parser.parse_args()
    
    main(username=args.username, client_id=args.client_id, song=args.song, all_tracks=args.all, sort_by=args.sort_by, num_tracks=args.num_tracks)