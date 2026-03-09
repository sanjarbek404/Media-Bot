from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import database as db

async def check_subscription(user_id: int, bot: Bot) -> list:
    """Checks if the user is subscribed to all mandatory channels. Returns list of channels they need to join."""
    channels = await db.get_all_channels()
    not_subscribed = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch['id'], user_id=user_id)
            if member.status in ['left', 'kicked']:
                not_subscribed.append(ch)
        except Exception as e:
            print(f"Error checking sub for {ch['id']}: {e}")
            # By failing closed (appending), users can't bypass if the channel ID is misconfigured
            not_subscribed.append(ch)
    return not_subscribed

def get_subscription_keyboard(unsub_channels):
    kb = []
    for i, ch in enumerate(unsub_channels):
        kb.append([InlineKeyboardButton(text=f"📢 {i+1}-Kanalga Obuna bo'lish", url=ch['url'])])
    
    kb.append([InlineKeyboardButton(text="✅ Obuna bo'ldim", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=kb)
