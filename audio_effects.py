import asyncio
import os
import uuid

# These paths assume ffmpeg is available in the system PATH
async def apply_audio_effect(input_path: str, effect_type: str) -> str:
    """
    Applies an audio effect using ffmpeg and returns the output file path.
    Supported effects: '8d', 'bass'
    """
    if not os.path.exists(input_path):
        return None
        
    output_filename = f"effect_{effect_type}_{uuid.uuid4().hex[:8]}.mp3"
    output_path = os.path.join(os.path.dirname(input_path), output_filename)
    
    # Define the ffmpeg audio filters based on effect type
    if effect_type == '8d':
        # apulsator creates a rotating 8D spatial audio effect
        filter_str = 'apulsator=hz=0.125'
    elif effect_type == 'bass':
        # bass boost
        filter_str = 'bass=g=15:f=110:w=0.3'
    else:
        return input_path # no-op
        
    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-af', filter_str,
        # copy codec configs could be adjusted, but since we re-encode by filtering:
        '-c:a', 'libmp3lame', '-q:a', '2', 
        output_path
    ]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        print(f"FFMPEG Error for {effect_type}: {stderr.decode()}")
        return None
        
    return output_path
