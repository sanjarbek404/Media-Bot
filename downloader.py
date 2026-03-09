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
}

async def download_video(url: str) -> str:
    file_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")
    
    ydl_opts: dict = BASE_YDL_OPTS.copy()
    if os.path.exists("cookies.txt"):
        ydl_opts['cookiefile'] = 'cookies.txt'
    else:
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'web']}}
    
    ydl_opts.update({
        'format': 'best[filesize<50M]/best',
        'outtmpl': output_template,
    })

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
        print(f"Error downloading video: {e}")
        return None

async def download_audio(url: str) -> str:
    """
    Downloads audio from the given URL using yt-dlp asynchronously.
    Returns the file path of the downloaded audio.
    """
    file_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f"{file_id}.%(ext)s")
    
    ydl_opts: dict = BASE_YDL_OPTS.copy()
    if os.path.exists("cookies.txt"):
        ydl_opts['cookiefile'] = 'cookies.txt'
    else:
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'web']}}
        
    ydl_opts.update({
        'format': 'best',
        'outtmpl': output_template,
    })

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
        print(f"Error downloading audio: {e}")
        return None

async def extract_metadata(url: str) -> dict:
    ydl_opts: dict = BASE_YDL_OPTS.copy()
    if os.path.exists("cookies.txt"):
        ydl_opts['cookiefile'] = 'cookies.txt'
    else:
        ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android', 'web']}}

    ydl_opts.update({
        'extract_flat': True,
    })

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
        print(f"Error extracting metadata: {e}")
        return None
