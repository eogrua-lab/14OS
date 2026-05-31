import asyncio
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey

# --- НАСТРОЙКИ ---
TOKEN = os.getenv('TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 6324212559))
BANNED_FILE = "banned_users.txt"

def get_banned_users():
    if not os.path.exists(BANNED_FILE): return set()
    with open(BANNED_FILE, "r") as f: return set(int(line.strip()) for line in f)

BANNED_USERS = get_banned_users()

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def log_message(user_id, category, message_text):
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_file = f"logs_{date_str}.txt"
    with open(log_file, "a", encoding="utf-8") as f: 
        f.write(f"({user_id}) {datetime.now().strftime('%H:%M:%S')} - {category} - {message_text}\n")

def storage_key(user_id: int) -> StorageKey:
    return StorageKey(bot_id=bot.id, user_id=user_id, chat_id=user_id)

# --- СОСТОЯНИЯ ---
class Feedback(StatesGroup):
    category = State()
    level = State()
    waiting_for_media = State()

class AdminReply(StatesGroup):
    waiting_for_admin_text = State()
    target_user_id = State()

# --- КЛАВИАТУРЫ ---
def admin_reply_kb(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Ответить", callback_data=f"rep_personal_{user_id}")],
        [InlineKeyboardButton(text="🚫 БАН", callback_data=f"ban_{user_id}")]
    ])

def user_reply_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Ответить разработчику", callback_data="user_reply_init")]
    ])

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def start(message: types.Message):
    if message.from_user.id in BANNED_USERS: return
    await message.answer("Привет! 14ОС на связи. Команды: /bug, /respect, /meet")

@dp.message(Feedback.waiting_for_media)
async def final_message(message: types.Message, state: FSMContext):
    if message.from_user.id in BANNED_USERS: return
    data = await state.get_data()
    cat = data.get('category', 'SUPPORT').upper()
    txt = message.text or (message.caption or "[МЕДИА]")
    log_message(message.from_user.id, cat, txt)
    
    await message.answer("✅ Отправлено! Если хочешь что-то добавить, нажми:", reply_markup=user_reply_kb())
    await bot.send_message(ADMIN_ID, f"✉️ {cat}\nID: `{message.from_user.id}`\nСообщение: {txt}", reply_markup=admin_reply_kb(message.from_user.id))
    await state.clear()

@dp.callback_query(F.data == "user_reply_init")
async def user_reply_start(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(category="REPLY")
    await state.set_state(Feedback.waiting_for_media)
    await callback.message.answer("Пиши ответ, он будет доставлен разработчику:")

@dp.callback_query(F.data.startswith("rep_personal_"))
async def handle_admin(callback: types.CallbackQuery, state: FSMContext):
    uid = callback.data.split("_")[2]
    await state.update_data(target_user_id=uid)
    await state.set_state(AdminReply.waiting_for_admin_text)
    await callback.message.answer(f"Пиши ответ для {uid} (/stop для выхода):")

@dp.message(AdminReply.waiting_for_admin_text)
async def admin_reply(message: types.Message, state: FSMContext):
    if message.text == "/stop":
        await state.clear()
        return await message.answer("🛑 Диалог окончен.")
    data = await state.get_data()
    await bot.send_message(data["target_user_id"], f"✉️ Ответ от 14OS:\n\n{message.text}", reply_markup=user_reply_kb())
    await message.answer("✅ Отправлено. /stop чтобы закончить.")

@dp.callback_query(F.data.startswith("ban_"))
async def ban(callback: types.CallbackQuery):
    uid = callback.data.split("_")[1]
    BANNED_USERS.add(int(uid))
    with open(BANNED_FILE, "a") as f: f.write(f"{uid}\n")
    await callback.message.edit_text(callback.message.text + f"\n\n🚫 {uid} В БАНЕ.")

@dp.message(Command("bug"))
async def cmd_bug(message: types.Message, state: FSMContext):
    await state.update_data(category="bug")
    await state.set_state(Feedback.waiting_for_media)
    await message.answer("Опиши баг:")

@dp.message(Command("respect"))
async def cmd_respect(message: types.Message, state: FSMContext):
    await state.update_data(category="respect")
    await state.set_state(Feedback.waiting_for_media)
    await message.answer("Присылай респект:")

@dp.message(Command("meet"))
async def cmd_meet(message: types.Message, state: FSMContext):
    await state.update_data(category="meet")
    await state.set_state(Feedback.waiting_for_media)
    await message.answer("Расскажи о себе:")

@dp.message(Command("reset"))
async def reset_state(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 2: return
    await dp.fsm.storage.set_state(key=storage_key(int(args[1])), state=None)
    await message.answer("Сброшено.")

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
