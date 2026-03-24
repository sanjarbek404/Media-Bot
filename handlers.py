import os
import re
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, FSInputFile, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter

from downloader import download_video, download_audio, extract_metadata
from shazam_service import identify_song
from yt_music_service import search_and_download_music, search_music_text # Re-added search_and_download_music and added search_music_text
import logging # Added logging
from locales import get_text, LANGUAGES
import uuid # Added uuid
import database as db
import admin_panel # Added admin_panel
from middlewares.subscription_check import check_subscription, get_subscription_keyboard # Added subscription check imports

# Load the bot from environment if needed to check subscriptions
BOT_TOKEN = os.getenv("BOT_TOKEN")

router = Router()
router.include_router(admin_panel.router) # Included admin_panel router

URL_REGEX = r'(https?://(?:www\.)?(?:instagram\.com|youtube\.com|youtu\.be|tiktok\.com|facebook\.com|fb\.com)[^\s]+)' # Updated URL_REGEX

def get_audio_fx_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎧 8D Audio", callback_data="fx_8d"),
         InlineKeyboardButton(text="🔊 Bass Boost", callback_data="fx_bass")]
    ])

@router.callback_query(F.data == "check_sub")
async def process_sub_check(callback: CallbackQuery, bot: Bot):
    lang = await db.get_user_lang(callback.from_user.id)
    unsub = await check_subscription(callback.from_user.id, bot)
    if unsub:
        await callback.answer(get_text('unsub_alert', lang), show_alert=True)
    else:
        await callback.message.delete()
        await callback.message.answer(get_text('sub_success', lang))

@router.message(Command("start"))
async def cmd_start(message: Message):
    is_new = not await db.user_exists(message.from_user.id)
    await db.add_user(message.from_user.id, message.from_user.first_name, message.from_user.username)
    lang = await db.get_user_lang(message.from_user.id)
    
    if is_new:
        # Generate language keyboard for new users
        kb = []
        for code, name in LANGUAGES.items():
            kb.append([InlineKeyboardButton(text=name, callback_data=f"set_lang_{code}")])
            
        await message.answer(
            get_text('choose_language', lang),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )
    else:
        # Just send welcome text
        await message.answer(get_text('welcome', lang))

@router.message(Command("lang"))
async def cmd_lang(message: Message):
    lang = await db.get_user_lang(message.from_user.id)
    kb = []
    for code, name in LANGUAGES.items():
        kb.append([InlineKeyboardButton(text=name, callback_data=f"set_lang_{code}")])
        
    await message.answer(
        get_text('choose_language', lang),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
    )

@router.callback_query(F.data.startswith("set_lang_"))
async def process_set_language(callback: CallbackQuery):
    lang_code = callback.data.replace("set_lang_", "")
    if lang_code in LANGUAGES:
        await db.set_user_lang(callback.from_user.id, lang_code)
        await callback.message.edit_text(get_text('lang_saved', lang_code))
    else:
        await callback.answer("Error")

@router.message(Command("help"))
async def cmd_help(message: Message):
    lang = await db.get_user_lang(message.from_user.id)
    await message.answer(get_text('help_text', lang))

@router.message(StateFilter(None), F.text & ~F.text.startswith("/"))
async def handle_message(message: Message, bot: Bot):
    # Log user interacting
    await db.add_user(message.from_user.id, message.from_user.first_name, message.from_user.username)
    lang = await db.get_user_lang(message.from_user.id)
    
    # Check mandatory sub
    unsub = await check_subscription(message.from_user.id, bot)
    if unsub:
        kb = []
        for i, ch in enumerate(unsub):
            kb.append([InlineKeyboardButton(text=get_text('sub_btn', lang, num=i+1), url=ch['url'])])
        kb.append([InlineKeyboardButton(text=get_text('sub_check', lang), callback_data="check_sub")])
        await message.answer(
            get_text('sub_required', lang),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )
        return

    text = message.text
    match = re.search(URL_REGEX, text)
    
    if match:
        await process_url_message(message, match.group(0))
    else:
        await process_text_search(message, text)

async def process_url_message(message: Message, url: str):
    lang = await db.get_user_lang(message.from_user.id)
    status_msg = await message.answer(get_text('wait', lang))

    # Download Video
    video_path, error_msg = await download_video(url)
    if not video_path:
        await status_msg.edit_text(f"{get_text('video_err', lang)}\n\n🛠 Xatolik tafsiloti:\n`{error_msg}`", parse_mode="Markdown")
        return

    # Create short id for callback
    short_id = await db.save_url_mapping(url)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text('find_music_btn', lang), callback_data=f"find_music_{short_id}")]
    ])
    
    try:
        video_file = FSInputFile(video_path)
        await message.answer_video(
            video=video_file,
            caption=get_text('uploaded_via', lang),
            reply_markup=keyboard
        )
        await status_msg.delete()
    except Exception as e:
        print(f"Video upload error: {e}")
        await status_msg.edit_text(get_text('unexpected_err', lang))
    finally:
        try:
            os.remove(video_path)
        except:
            pass

async def process_text_search(message: Message, query: str):
    """
    Searches YouTube for the query and presents 10 options as inline buttons.
    """
    lang = await db.get_user_lang(message.from_user.id)
    status_msg = await message.answer(get_text('searching_btn', lang))
    results = await search_music_text(query, limit=10) # Changed __import__('yt_music_service').search_music_text to search_music_text
    
    await status_msg.delete()
    
    if not results:
        await message.answer(get_text('not_found', lang))
        return
        
    buttons = []
    # Maximum 10 results
    for i, res in enumerate(results[:10]):
        # Save URL to db for short callback data
        short_id = await db.save_url_mapping(res['url'])
        title_trunc = res['title'][:50] + '...' if len(res['title']) > 50 else res['title']
        btn_text = f"{i+1}. {title_trunc} ({res['duration']})"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"dl_music_{short_id}")])
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        get_text('select_music', lang),
        reply_markup=keyboard
    )
    
@router.callback_query(F.data.startswith("find_music_"))
async def process_find_music(callback: CallbackQuery):
    lang = await db.get_user_lang(callback.from_user.id)
    short_id = callback.data.replace("find_music_", "")
    url = await db.get_url_from_mapping(short_id)
    
    if not url:
        await callback.answer(get_text('expired_link', lang), show_alert=True)
        return

    # Delete the inline button that was clicked
    await callback.message.edit_reply_markup(reply_markup=None)
    status_msg = await callback.message.reply(get_text('extract_audio', lang))

    try:
        # Parallel Process: Download Audio snippet & Extract Metadata
        audio_task = asyncio.create_task(download_audio(url))
        meta_task = asyncio.create_task(extract_metadata(url))
        
        snippet_path, metadata = await asyncio.gather(audio_task, meta_task)
        
        if not snippet_path:
            await status_msg.edit_text(get_text('video_err', lang))
            return

        # Identify via Shazam
        shazam_info = await identify_song(snippet_path)
        
        # Cleanup snippet
        try:
            os.remove(snippet_path)
        except Exception:
            pass

        title = None
        artist = None
        found_track_id = None

        if shazam_info:
            title = shazam_info['title']
            artist = shazam_info['artist']
            found_track_id = shazam_info.get('track_id')
        elif metadata and metadata.get('title'):
            # Fallback to metadata if Shazam failed
            title = metadata['title']
            artist = metadata.get('artist', 'Noma\'lum Ijrochi')
            found_track_id = f"{title}_{artist}"
        else:
            await status_msg.edit_text(get_text('not_found', lang))
            return

        # Search and download full track from Youtube
        full_music_path = await search_and_download_music(title, artist)

        if not full_music_path:
            await status_msg.edit_text(get_text('not_found', lang))
            return

        # Upload
        file_name = os.path.basename(full_music_path)
        clean_name = file_name.split("_dl_", 1)[-1] if "_dl_" in file_name else file_name
        audio_file = FSInputFile(full_music_path, filename=clean_name)
        
        await callback.message.answer_audio(
            audio=audio_file,
            caption=f"🎵 {title} - {artist}\n" + get_text('music_found_via', lang),
            performer=artist,
            title=title,
            reply_markup=get_audio_fx_keyboard()
        )

        await status_msg.delete()

        # Cleanup full music
        try:
            os.remove(full_music_path)
        except:
            pass

    except Exception as e:
        print(f"Error in find music handler: {e}")
        await status_msg.edit_text(get_text('unexpected_err', lang))

@router.callback_query(F.data.startswith("dl_music_"))
async def process_download_music(callback: CallbackQuery):
    lang = await db.get_user_lang(callback.from_user.id)
    short_id = callback.data.replace("dl_music_", "")
    url = await db.get_url_from_mapping(short_id)
    
    if not url:
        await callback.answer(get_text('expired_link', lang), show_alert=True)
        return

    # await callback.message.edit_reply_markup(reply_markup=None) # Removed this line to persist the button
    status_msg = await callback.message.reply(get_text('wait', lang))

    try:
        # We consider the url directly to download the full track
        full_music_path = await search_and_download_music("", url=url) # Changed __import__('yt_music_service').search_and_download_music to search_and_download_music
        # Edit keyboard back to persist "Find Music" button
        await status_msg.delete()
        
        # Audio
        # Rename the file to {title}.mp3 format inside yt_music_service instead of random file hash
        
        if not full_music_path:
            await callback.message.answer(get_text('not_found', lang)) # Changed edit_text to answer
            return

        # Clean file name for Telegram
        file_name = os.path.basename(full_music_path)
        clean_name = file_name.split("_dl_", 1)[-1] if "_dl_" in file_name else file_name
        audio_file = FSInputFile(full_music_path, filename=clean_name)
        await callback.message.answer_audio(
            audio=audio_file,
            caption=get_text('uploaded_via', lang),
            reply_markup=get_audio_fx_keyboard()
        )

        # Cleanup
        try:
            os.remove(full_music_path)
        except:
            pass

    except Exception as e:
        print(f"Error in direct download handler: {e}")
        await status_msg.edit_text(get_text('unexpected_err', lang))

@router.callback_query(F.data.startswith("fx_"))
async def handle_audio_effect(callback: CallbackQuery, bot: Bot):
    lang = await db.get_user_lang(callback.from_user.id)
    effect = callback.data.replace("fx_", "")
    if not callback.message.audio:
        await callback.answer(get_text('no_audio', lang), show_alert=True)
        return
        
    await callback.answer(f"{effect.upper()}...", show_alert=False)
    status_msg = await callback.message.reply(get_text('fx_wait', lang))
    
    file_id = callback.message.audio.file_id
    title = callback.message.audio.title or "Audio"
    performer = callback.message.audio.performer or ""
    
    try:
        file_info = await bot.get_file(file_id)
        os.makedirs("downloads", exist_ok=True)
        file_path = f"downloads/{file_id[:15]}.mp3"
        await bot.download_file(file_info.file_path, destination=file_path)
        
        from audio_effects import apply_audio_effect
        processed_file = await apply_audio_effect(file_path, effect)
        
        if not processed_file:
            await status_msg.edit_text(get_text('fx_err', lang))
        else:
            await status_msg.delete()
            await callback.message.answer_audio(
                audio=FSInputFile(processed_file, filename=f"{title} ({effect.upper()}).mp3"),
                caption=get_text('fx_success', lang, effect=effect.upper()),
                title=f"{title} ({effect.upper()})",
                performer=performer
            )
            os.remove(processed_file)
            
        try:
            os.remove(file_path)
        except:
            pass
    except Exception as e:
        print(f"Error applying fx {effect}: {e}")
        await status_msg.edit_text(get_text('fx_limit_err', lang))

@router.message(F.audio | F.video | F.voice | F.document)
async def handle_direct_media(message: Message, bot: Bot):
    await db.add_user(message.from_user.id, message.from_user.first_name, message.from_user.username)
    lang = await db.get_user_lang(message.from_user.id)

    unsub = await check_subscription(message.from_user.id, bot)
    if unsub:
        kb = []
        for i, ch in enumerate(unsub):
            kb.append([InlineKeyboardButton(text=get_text('sub_btn', lang, num=i+1), url=ch['url'])])
        kb.append([InlineKeyboardButton(text=get_text('sub_check', lang), callback_data="check_sub")])
        await message.answer(
            get_text('sub_required', lang),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )
        return

    status_msg = await message.answer(get_text('extract_audio', lang))
    
    # 1. Download the media
    try:
        if message.audio:
            file_id = message.audio.file_id
        elif message.video:
            file_id = message.video.file_id
        elif message.voice:
            file_id = message.voice.file_id
        elif message.document:
            file_id = message.document.file_id
        else:
            return

        file_info = await bot.get_file(file_id)
        os.makedirs("downloads", exist_ok=True)
        local_path = f"downloads/{file_id[:15]}_direct.tmp"
        await bot.download_file(file_info.file_path, destination=local_path)
    except Exception as e:
        print(f"Error downloading direct media: {e}")
        await status_msg.edit_text(get_text('video_err', lang))
        return

    # 2. Shazam identification
    try:
        shazam_info = await identify_song(local_path)
    except Exception as e:
        print(f"Shazam error: {e}")
        shazam_info = None
        
    try:
        os.remove(local_path)
    except:
        pass

    if not shazam_info:
        await status_msg.edit_text(get_text('not_found', lang))
        return
        
    title = shazam_info['title']
    artist = shazam_info['artist']

    # 3. Search and Download
    await status_msg.edit_text(get_text('searching_btn', lang))
    full_music_path = await search_and_download_music(title, artist)
    
    if not full_music_path:
        await status_msg.edit_text(get_text('not_found', lang))
        return

    # 4. Upload
    try:
        file_name = os.path.basename(full_music_path)
        clean_name = file_name.split("_dl_", 1)[-1] if "_dl_" in file_name else file_name
        audio_file = FSInputFile(full_music_path, filename=clean_name)
        
        await message.answer_audio(
            audio=audio_file,
            caption=f"🎵 {title} - {artist}\n" + get_text('music_found_via', lang),
            performer=artist,
            title=title,
            reply_markup=get_audio_fx_keyboard()
        )
        await status_msg.delete()
    except Exception as e:
        print(f"Upload err: {e}")
        await status_msg.edit_text(get_text('unexpected_err', lang))
    finally:
        try:
            os.remove(full_music_path)
        except:
            pass
