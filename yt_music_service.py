import asyncio
import os
import uuid
import yt_dlp

MUSIC_DIR = "music"
os.makedirs(MUSIC_DIR, exist_ok=True)

async def search_and_download_music(title: str, artist: str = "", url: str = None) -> str:
    """
    Downloads music from a direct url if provided, else searches YouTube.
    """
    url_or_query = url if url else f"ytsearch1:{title} {artist} audio"
    file_id = str(uuid.uuid4())[:8]
    # Use actual title and limit length to avoid OS Path Too Long errors
    output_template = os.path.join(MUSIC_DIR, f"{file_id}_dl_%(title).50s.%(ext)s")
    
    ydl_opts = {
        'format': 'best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    if os.path.exists("cookies.txt"):
        ydl_opts['cookiefile'] = 'cookies.txt'
    else:
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android']}}

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url_or_query, download=True)
            return file_id

    try:
        f_id = await asyncio.to_thread(_download)
        # yt-dlp replaces characters in real titles, so we search by our prefix
        search_prefix = f"{f_id}_dl_"
        for file in os.listdir(MUSIC_DIR):
            if file.startswith(search_prefix):
                return os.path.join(MUSIC_DIR, file)
        return None
    except Exception as e:
        print(f"Error searching/downloading music: {e}")
        return None

async def search_music_text(query: str, limit: int = 10) -> list:
    """
    Searches YouTube for the given text query and returns a list of dictionaries 
    containing the title, duration, and URL limit times.
    """
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'quiet': True,
        'no_warnings': True,
    }
    if os.path.exists("cookies.txt"):
        ydl_opts['cookiefile'] = 'cookies.txt'
    else:
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android']}}
    
    def _search():
        search_query = f"ytsearch{limit}:{query}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            if 'entries' in info:
                results = []
                for entry in info['entries']:
                    title = entry.get('title')
                    url = entry.get('url')
                    duration = entry.get('duration')
                    # Basic duration formatting
                    if duration and int(duration) <= 1200: # Skip everything longer than 20 minutes
                        mins, secs = divmod(int(duration), 60)
                        dur_str = f"{mins}:{secs:02d}"
                    
                        if title and url:
                            results.append({
                                'title': title,
                                'url': url,
                                'duration': dur_str
                            })
                return results
            return []
            
    try:
        return await asyncio.to_thread(_search)
    except Exception as e:
        print(f"Error executing text search: {e}")
        return []
