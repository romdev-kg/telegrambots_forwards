import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from db import Database
import datetime

logging.basicConfig(level=logging.INFO)

bot = Bot(token='6473316210:AAG2FF9IlKc2WPuVsS86sEhRonONgTKewMs', parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())
db = Database('database.db')

class BroadcastState(StatesGroup):
    waiting_for_images = State()
    waiting_for_description = State()
    waiting_for_time = State()

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    if message.chat.type == 'private':
        if not db.user_exists(message.from_user.id):
            db.add_user(message.from_user.id)
        await bot.send_message(message.from_user.id, 'Welcome!')

@dp.message_handler(commands=['broadcast'], user_id=5616197578)
async def cmd_broadcast(message: types.Message):
    await BroadcastState.waiting_for_images.set()
    await message.answer("Please send me the images for the broadcast. Send /done when finished or /skip to skip images.")

@dp.message_handler(content_types=['photo'], state=BroadcastState.waiting_for_images)
async def handle_images(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if 'photos' not in data:
            data['photos'] = []
        data['photos'].append(message.photo[-1].file_id)
    await message.answer("Image received. You can send more images or send /done to finish.")

@dp.message_handler(commands=['done'], state=BroadcastState.waiting_for_images)
async def finish_images(message: types.Message, state: FSMContext):
    await BroadcastState.next()
    await message.answer("Now send me the description. You can use HTML formatting for links.")

@dp.message_handler(commands=['skip'], state=BroadcastState.waiting_for_images)
async def skip_images(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['photos'] = []
    await BroadcastState.next()
    await message.answer("Images skipped. Now send me the description. You can use HTML formatting for links.")

@dp.message_handler(state=BroadcastState.waiting_for_description, content_types=types.ContentTypes.TEXT)
async def handle_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['description'] = message.text

    await BroadcastState.next()
    await message.answer("Please send me the time for the broadcast in the format 'YYYY-MM-DD HH:MM'.")

@dp.message_handler(state=BroadcastState.waiting_for_time, content_types=types.ContentTypes.TEXT)
async def handle_time(message: types.Message, state: FSMContext):
    try:
        broadcast_time = datetime.datetime.strptime(message.text, '%Y-%m-%d %H:%M')
    except ValueError:
        await message.answer("Invalid time format. Please use 'YYYY-MM-DD HH:MM'.")
        return

    async with state.proxy() as data:
        data['time'] = broadcast_time

    photos = data.get('photos', [])
    description = data['description']
    await schedule_broadcast(photos, description, broadcast_time)

    await message.answer(f"Broadcast scheduled successfully for {broadcast_time}!")
    await state.finish()

async def schedule_broadcast(photos, description, broadcast_time):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(broadcast_message, 'date', run_date=broadcast_time, args=[photos, description])
    scheduler.start()

async def broadcast_message(photos, description):
    users = db.get_users()
    groups = db.get_groups()

    for row in users:
        try:
            if photos:
                media = [types.InputMediaPhoto(photo, caption=description if i == 0 else '') for i, photo in enumerate(photos)]
                await bot.send_media_group(row[0], media)
            else:
                await bot.send_message(row[0], description)
            if int(row[1]) != 1:
                db.set_active(row[0], 1)
        except Exception as e:
            db.set_active(row[0], 0)
            print(f"Failed to send message to {row[0]}: {e}")

    for row in groups:
        try:
            if photos:
                media = [types.InputMediaPhoto(photo, caption=description if i == 0 else '') for i, photo in enumerate(photos)]
                await bot.send_media_group(row[0], media)
            else:
                await bot.send_message(row[0], description)
            if int(row[1]) != 1:
                db.set_active(row[0], 1, is_user=False)
        except Exception as e:
            db.set_active(row[0], 0, is_user=False)
            print(f"Failed to send message to group {row[0]}: {e}")

@dp.message_handler(content_types=types.ContentTypes.NEW_CHAT_MEMBERS)
async def new_chat_member(message: types.Message):
    for new_member in message.new_chat_members:
        if new_member.id == bot.id:
            if not db.group_exists(message.chat.id):
                db.add_group(message.chat.id)
            await bot.send_message(message.chat.id, 'Hello everyone!')

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
    db.close()
