import asyncio
import os
import uuid
import yt_dlp

MUSIC_DIR = "music"
os.makedirs(MUSIC_DIR, exist_ok=True)

BASE_YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'extractor_args': {'youtube': {'player_client': ['android']}},
}

def _get_ydl_opts() -> dict:
    """Build yt-dlp options with dynamic cookie and extractor_args."""
    opts = BASE_YDL_OPTS.copy()
    if os.path.exists("cookies.txt"):
        opts['cookiefile'] = 'cookies.txt'
    return opts

def _get_ydl_opts_no_cookies() -> dict:
    """Build yt-dlp options WITHOUT cookies (fallback)."""
    return BASE_YDL_OPTS.copy()

async def search_and_download_music(title: str, artist: str = "", url: str = None) -> str:
    """
    Downloads music from a direct url if provided, else searches YouTube.
    """
    url_or_query = url if url else f"ytsearch1:{title} {artist} audio"
    file_id = str(uuid.uuid4())[:8]
    output_template = os.path.join(MUSIC_DIR, f"{file_id}_dl_%(title).50s.%(ext)s")

    for get_opts in [_get_ydl_opts, _get_ydl_opts_no_cookies]:
        ydl_opts = get_opts()
        ydl_opts['format'] = 'best'
        ydl_opts['outtmpl'] = output_template
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url_or_query, download=True)
                return file_id

        try:
            f_id = await asyncio.to_thread(_download)
            for file in os.listdir(MUSIC_DIR):
                if file.startswith(f_id):
                    return os.path.join(MUSIC_DIR, file)
            return None
        except Exception as e:
            print(f"Error searching/downloading music (retrying without cookies): {e}")
            continue
    return None

async def search_music_text(query: str, limit: int = 10) -> list:
    """
    Searches YouTube for the given text query and returns a list of dictionaries.
    """
    for get_opts in [_get_ydl_opts, _get_ydl_opts_no_cookies]:
        ydl_opts = get_opts()
        ydl_opts['extract_flat'] = 'in_playlist'

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
                        if duration and int(duration) <= 1200:
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
            print(f"Error executing text search (retrying without cookies): {e}")
            continue
    return []
