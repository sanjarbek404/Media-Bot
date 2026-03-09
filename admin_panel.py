from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os
import database as db

router = Router()

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
except:
    ADMIN_ID = 0

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_channel_id = State()
    waiting_for_channel_url = State()

def get_admin_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📨 Reklama Tarqatish", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📢 Majburiy Obuna kanallari", callback_data="admin_channels")]
    ])

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(
        "👨‍💻 <b>Admin Panelga xush kelibsiz!</b>\nQuyidagi menyudan kerakli bo'limni tanlang:",
        reply_markup=get_admin_main_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
        
    user_count = await db.get_user_count()
    await callback.message.edit_text(
        f"📊 <b>Bot Statistikasi:</b>\n\n👥 Umumiy foydalanuvchilar soni: <b>{user_count}</b> ta",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]]),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
        
    await callback.message.edit_text(
        "📝 Barcha foydalanuvchilarga yuboriladigan xabarni (matn, rasm yoki video) yuboring:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_back")]])
    )
    await state.set_state(AdminStates.waiting_for_broadcast)

@router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        return
        
    users = await db.get_all_users()
    success = 0
    fail = 0
    
    status_msg = await message.answer(f"⏳ Xabar tarqatilmoqda... (Jami: {len(users)})")
    
    for user_id in users:
        try:
            await message.send_copy(chat_id=user_id)
            success += 1
        except Exception:
            fail += 1
            
    await status_msg.edit_text(
        f"✅ <b>Reklama tarqatildi!</b>\n\n"
        f"Muaffaqiyatli: {success} ta\n"
        f"Yetib bormadi (Bloklaganlar): {fail} ta",
        reply_markup=get_admin_main_kb(),
        parse_mode="HTML"
    )
    await state.clear()

# --- Channels ---
def get_channels_kb(channels):
    kb = []
    for ch in channels:
        kb.append([InlineKeyboardButton(text=f"🗑 O'chirish: {ch['id']}", callback_data=f"del_ch_{ch['id']}")])
        
    kb.append([InlineKeyboardButton(text="➕ Yangi kanal qo'shish", callback_data="add_channel")])
    kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.callback_query(F.data == "admin_channels")
async def admin_channels(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
        
    channels = await db.get_all_channels()
    msg = "📢 <b>Majburiy Obuna Kanallari:</b>\n\n"
    if not channels:
        msg += "⚠️ Hozircha majburiy kanallar yo'q."
    else:
        for ch in channels:
            msg += f"🔸 ID: <code>{ch['id']}</code> | Link: {ch['url']}\n"
            
    await callback.message.edit_text(msg, reply_markup=get_channels_kb(channels), parse_mode="HTML")

@router.callback_query(F.data == "add_channel")
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
        
    await callback.message.edit_text(
        "➕ Yangi kanalni qo'shish uchun uning ID sini yuboring:\n(Masalan: <code>-1001234567890</code> yoki <code>@kanal_uz</code>)\n\n"
        "<i>Eslatma: Bot o'sha kanalga admin qilinishi e-shart!</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_channels")]])
    )
    await state.set_state(AdminStates.waiting_for_channel_id)

@router.message(AdminStates.waiting_for_channel_id)
async def process_channel_id(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
        
    ch_id = message.text.strip()
    if ch_id.startswith("https://t.me/"):
        target = ch_id.split("/")[-1]
        if not target.startswith("+") and not target.startswith("joinchat"):
            ch_id = f"@{target}"

    await state.update_data(channel_id=ch_id)
    await message.answer(
        "🔗 Endi shu kanalning havolasini (link) yuboring:\n(Masalan: <code>https://t.me/kanal_uz</code>)",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_channels")]])
    )
    await state.set_state(AdminStates.waiting_for_channel_url)

@router.message(AdminStates.waiting_for_channel_url)
async def process_channel_url(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
        
    data = await state.get_data()
    channel_id = data['channel_id']
    channel_url = message.text
    
    await db.add_channel(channel_id, channel_url)
    
    await message.answer("✅ Kanal muvaffaqiyatli qo'shildi!", reply_markup=get_admin_main_kb())
    await state.clear()

@router.callback_query(F.data.startswith("del_ch_"))
async def del_channel(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
        
    ch_id = callback.data.replace("del_ch_", "")
    await db.remove_channel(ch_id)
    await callback.answer(f"✅ Kanal ({ch_id}) o'chirildi!", show_alert=True)
    await admin_channels(callback) # refresh list

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
        
    await state.clear()
    await callback.message.edit_text(
        "👨‍💻 <b>Admin Panelga xush kelibsiz!</b>\nQuyidagi menyudan kerakli bo'limni tanlang:",
        reply_markup=get_admin_main_kb(),
        parse_mode="HTML"
    )
