import asyncio
import os
import uuid
import yt_dlp

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Common options against anti-bot
BASE_YDL_OPTS = {
    'nopart': True, # Fixes WinError 32 on Windows by not creating .part files
    'quiet': True,
    'no_warnings': True,
    'extractor_args': {'youtube': {'player_client': ['android', 'ios']}},
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

async def download_video(url: str) -> str:
    file_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

    for get_opts in [_get_ydl_opts, _get_ydl_opts_no_cookies]:
        ydl_opts = get_opts()
        ydl_opts['format'] = 'best[height<=720][ext=mp4]/best[ext=mp4]/best'
        ydl_opts['outtmpl'] = output_template

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)
                return file_id

        try:
            f_id = await asyncio.to_thread(_download)
            for file in os.listdir(DOWNLOAD_DIR):
                if file.startswith(f_id):
                    return os.path.join(DOWNLOAD_DIR, file)
            return None
        except Exception as e:
            print(f"Error downloading video (retrying without cookies): {e}")
            continue  # Try next opts set
    return None

async def download_audio(url: str) -> str:
    """
    Downloads audio from the given URL using yt-dlp asynchronously.
    Returns the file path of the downloaded audio.
    """
    file_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")

    for get_opts in [_get_ydl_opts, _get_ydl_opts_no_cookies]:
        ydl_opts = get_opts()
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['outtmpl'] = output_template

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)
                return file_id

        try:
            f_id = await asyncio.to_thread(_download)
            for file in os.listdir(DOWNLOAD_DIR):
                if file.startswith(f_id):
                    return os.path.join(DOWNLOAD_DIR, file)
            return None
        except Exception as e:
            print(f"Error downloading audio (retrying without cookies): {e}")
            continue
    return None

async def extract_metadata(url: str) -> dict:
    for get_opts in [_get_ydl_opts, _get_ydl_opts_no_cookies]:
        ydl_opts = get_opts()
        ydl_opts['extract_flat'] = True

        def _extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            info = await asyncio.to_thread(_extract)
            if info:
                track = info.get('track') or info.get('title')
                artist = info.get('artist') or info.get('uploader')
                if track:
                    return {
                        'title': track,
                        'artist': artist
                    }
            return None
        except Exception as e:
            print(f"Error extracting metadata (retrying without cookies): {e}")
            continue
    return None
