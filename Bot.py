import json
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext, filters
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
import aioschedule
import asyncio
import datetime

API_TOKEN = '7713619641:AAFBHyOkNObEKVsq6sUk4VbsoFUJEpx9z7s'

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создание объектов бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
Bot.set_current(bot)

# Файл для хранения данных
DATA_FILE = 'Data.json'

# Загрузка данных из файла
def load_data():
    try:
        with open(DATA_FILE, 'r', encoding="UTF-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Сохранение данных в файл
def save_data(data):
    with open(DATA_FILE, 'w', encoding="UTF-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Команда /start
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.answer("Привет! Я бот для ведения личного дневника. Используй команды:\n"
                         "/add 'текст заметки'\n"
                         "/list - список заметок\n"
                         "/done 'номер заметки' - пометить как выполненную\n"
                         "/remind 'номер заметки' 'дд/мм чч:мм' - установить напоминание\n")

# Команда для добавления заметок
@dp.message_handler(commands=['add'])
async def add_note_command(message: types.Message):
    text = message.get_args()
    if not text:
        await message.answer("Пожалуйста, укажите текст заметки.")
        return

    data = load_data()
    user_id = str(message.from_user.id)
    if user_id not in data:
        data[user_id] = {'notes': []}

    note = {'text': text, 'done': False}
    data[user_id]['notes'].append(note)
    save_data(data)

    await message.answer("Заметка добавлена!")

# Команда для просмотра заметок
@dp.message_handler(commands=['list'])
async def list_notes_command(message: types.Message):
    data = load_data()
    user_id = str(message.from_user.id)
    if user_id not in data or not data[user_id]['notes']:
        await message.answer("У вас нет заметок.")
        return

    notes = data[user_id]['notes']
    notes_text = "\n".join(f"{i + 1}. [{'✅' if note['done'] else '❌'}] {note['text']}" for i, note in enumerate(notes))
    await message.answer("Ваши заметки:\n" + notes_text)

# Команда для пометки заметки как выполненной
@dp.message_handler(commands=['done'])
async def done_note_command(message: types.Message):
    args = message.get_args()
    if not args.isdigit():
        await message.answer("Пожалуйста, укажите номер заметки.")
        return

    note_index = int(args) - 1
    data = load_data()
    user_id = str(message.from_user.id)

    if user_id not in data or note_index < 0 or note_index >= len(data[user_id]['notes']):
        await message.answer("Заметка не найдена.")
        return

    data[user_id]['notes'][note_index]['done'] = True
    save_data(data)

    await message.answer("Заметка помечена как выполненная!")

# Команда для установки напоминания
@dp.message_handler(commands=['remind'])
async def remind_note_command(message: types.Message):
    args = message.get_args().split(' ', 1)
    if len(args) != 2 or not args[0].isdigit():
        await message.answer("Использование: /remind 'номер заметки' 'дд/мм чч:мм'")
        return

    note_index = int(args[0]) - 1
    reminder_input = args[1]

    try:
        reminder_date_str, reminder_time_str = reminder_input.split(' ')
        reminder_day, reminder_month = map(int, reminder_date_str.split('/'))
        reminder_hour, reminder_minute = map(int, reminder_time_str.split(':'))
        reminder_datetime = datetime.datetime(datetime.datetime.now().year, reminder_month, 
                                              reminder_day, reminder_hour, reminder_minute)
    except ValueError:
        await message.answer("Неверный формат. Используйте 'дд/мм чч:мм'.")
        return

    data = load_data()
    user_id = str(message.from_user.id)

    if user_id not in data or note_index < 0 or note_index >= len(data[user_id]['notes']):
        await message.answer("Заметка не найдена.")
        return

    note_text = data[user_id]['notes'][note_index]['text']
    
    # Установка напоминания
    async def job():
        await message.answer(f"Напоминание: {note_text}")

    aioschedule.every().day.at(reminder_datetime.strftime('%H:%M')).do(job)

    await message.answer(f"Напоминание установлено на {reminder_datetime.strftime('%d/%m %H:%M')}!")

# Функция для запуска планировщика
async def scheduler():
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(scheduler())
    executor.start_polling(dp, skip_updates=True)
    