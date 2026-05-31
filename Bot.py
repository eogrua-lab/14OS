import asyncio
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
# ВОТ ЭТОЙ СТРОКИ, СКОРЕЕ ВСЕГО, НЕ ХВАТАЕТ:
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton 
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- НАСТРОЙКИ ---
TOKEN = os.getenv('TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
LANG = "ru"

TEXTS = {
    "ru": {
        "start": "Привет! Ты нашел секретный канал связи 14ОС. Выбирай:",
        "cat_bug": "🐞 Нашел баг",
        "cat_praise": "🔥 Выразить респект",
        "cat_meet": "🤝 Познакомиться",
        "bug_crit": "❗️ Критически",
        "bug_minor": "⚠️ Немного мешает",
        "prompt_bug": "Ого, ошибка? Насколько она серьезна?",
        "prompt_text": "Принято. Присылай текст, фото или видео:",
        "success": "✅ ОТПРАВЛЕНО!"
    }
}

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class Feedback(StatesGroup):
    category = State()
    level = State()
    waiting_for_media = State()

# --- КЛАВИАТУРЫ ---
def main_kb():
    t = TEXTS[LANG]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["cat_bug"], callback_data="cat_bug")],
        [InlineKeyboardButton(text=t["cat_praise"], callback_data="cat_praise")],
        [InlineKeyboardButton(text=t["cat_meet"], callback_data="cat_meet")]
    ])

def bug_kb():
    t = TEXTS[LANG]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["bug_crit"], callback_data="bug_crit")],
        [InlineKeyboardButton(text=t["bug_minor"], callback_data="bug_minor")]
    ])

# --- ЛОГИКА ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(TEXTS[LANG]["start"], reply_markup=main_kb())

@dp.callback_query(F.data.startswith("cat_"))
async def handle_category(callback: types.CallbackQuery, state: FSMContext):
    cat = callback.data.split("_")[1]
    await state.update_data(category=cat)
    if cat == "bug":
        await callback.message.answer(TEXTS[LANG]["prompt_bug"], reply_markup=bug_kb())
    else:
        await state.set_state(Feedback.waiting_for_media)
        await callback.message.answer(TEXTS[LANG]["prompt_text"])
    await callback.answer()

@dp.callback_query(F.data.startswith("bug_"))
async def handle_bug_level(callback: types.CallbackQuery, state: FSMContext):
    level = "КРИТИЧЕСКИ ❗️" if callback.data == "bug_crit" else "МЕЛКИЙ БАГ ⚠️"
    await state.update_data(level=level)
    await state.set_state(Feedback.waiting_for_media)
    await callback.message.answer(TEXTS[LANG]["prompt_text"])
    await callback.answer()

# --- УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК (принимает ВСЁ) ---
@dp.message(Feedback.waiting_for_media)
async def final_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cat = data.get('category').upper()
    lvl = f" | {data.get('level')}" if data.get('level') else ""
    username = f"@{message.from_user.username}" if message.from_user.username else "NoName"
    
    header = f"✉️ {cat}{lvl}\n👤 Юзер: {username}\n🆔 ID: `{message.from_user.id}`"
    
    # Пересылаем сообщение целиком (это сохранит фото/видео/текст)
    await bot.send_message(chat_id=ADMIN_ID, text=f"{header}\n\n💬 Вложение:")
    await bot.copy_message(chat_id=ADMIN_ID, from_chat_id=message.chat.id, message_id=message.message_id)
    
    await message.answer(TEXTS[LANG]["success"])
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
