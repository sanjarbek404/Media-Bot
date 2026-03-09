from shazamio import Shazam

async def identify_song(filepath: str) -> dict:
    """
    Identifies the song from the given audio file using shazamio.
    Returns a dictionary with 'title' and 'artist' if found, else None.
    """
    shazam = Shazam()
    try:
        out = await shazam.recognize(filepath)
        if 'track' in out:
            track = out['track']
            title = track.get('title', 'Unknown Title')
            artist = track.get('subtitle', 'Unknown Artist')
            track_id = track.get('key', None)
            return {
                'title': title,
                'artist': artist,
                'track_id': track_id
            }
        return None
    except Exception as e:
        print(f"Error identifying song: {e}")
        return None
