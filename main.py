import os
import telebot
import requests
import json
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========== БЕРЕМ ДАННЫЕ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
FOLDER_ID = os.getenv("FOLDER_ID")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Проверка, что все переменные загружены
if not all([BOT_TOKEN, YANDEX_API_KEY, FOLDER_ID, ADMIN_ID]):
    print("❌ ОШИБКА: Не все переменные окружения загружены!")
    print("Убедись, что на Render добавлены:")
    print("BOT_TOKEN, YANDEX_API_KEY, FOLDER_ID, ADMIN_ID")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# Хранилище пользователей
user_messages = {}

SYSTEM_PROMPT = """Ты — профессиональный аналитик и эксперт.
Отвечай глубоко, структурированно, с фактами и примерами.
Пиши как университетский лектор, не как школьник."""

# ========== КНОПКИ ДЛЯ АДМИНА ==========
def admin_panel():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📊 Статистика", callback_data="stats"))
    keyboard.add(InlineKeyboardButton("👥 Пользователи", callback_data="users"))
    keyboard.add(InlineKeyboardButton("📨 Рассылка", callback_data="broadcast"))
    return keyboard

# ========== ОБРАБОТКА КНОПОК ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Только для админа!")
        return
    
    if call.data == "stats":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, 
            f"📊 **Статистика**\n\n"
            f"👥 Пользователей: {len(user_messages)}\n"
            f"⏱ Последний: {time.strftime('%H:%M:%S')}"
        )
    
    elif call.data == "users":
        bot.answer_callback_query(call.id)
        if user_messages:
            users_list = "\n".join([f"👤 @{u.get('username', 'без username')}" 
                                   for u in list(user_messages.values())[-10:]])
            bot.send_message(call.message.chat.id, f"👥 **Последние 10:**\n\n{users_list}")
        else:
            bot.send_message(call.message.chat.id, "📭 Нет пользователей")
    
    elif call.data == "broadcast":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "✏️ Введите текст для рассылки:")
        bot.register_next_step_handler(call.message, send_broadcast)

# ========== РАССЫЛКА ==========
def send_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    sent = 0
    for user_id in user_messages.keys():
        try:
            bot.send_message(user_id, f"📢 **Объявление:**\n\n{message.text}")
            sent += 1
            time.sleep(0.05)
        except:
            pass
    bot.reply_to(message, f"✅ Отправлено {sent} пользователям!")

# ========== КОМАНДА START ==========
@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "👑 **Админ-панель**\n\nВыбери действие:", reply_markup=admin_panel())
    else:
        bot.reply_to(message, 
            "👋 Привет! Я ИИ-помощник на YandexGPT.\n\n"
            "Пиши любой запрос — я помогу! 🚀"
        )

# ========== ОБРАБОТКА ВСЕХ СООБЩЕНИЙ ==========
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    # Сохраняем пользователя
    user_messages[message.from_user.id] = {
        'user_id': message.from_user.id,
        'username': message.from_user.username,
        'last_message': message.text[:100],
        'last_time': time.time()
    }
    
    # Если админ написал не команду — показываем меню
    if message.from_user.id == ADMIN_ID:
        if message.text.startswith('/'):
            return
        bot.reply_to(message, "👑 Админ-панель:", reply_markup=admin_panel())
        return
    
    # Отправляем запрос пользователя админу в боте
    try:
        bot.send_message(
            ADMIN_ID,
            f"📩 **Новое сообщение**\n"
            f"👤 @{message.from_user.username or 'без username'}\n"
            f"🆔 ID: {message.from_user.id}\n"
            f"📝 {message.text[:300]}\n"
            f"⏰ {time.strftime('%H:%M:%S %d.%m.%Y')}"
        )
    except:
        pass
    
    # === ОТВЕЧАЕМ ПОЛЬЗОВАТЕЛЮ ===
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        headers = {
            "Authorization": f"Api-Key {YANDEX_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
            "completionOptions": {
                "stream": False,
                "temperature": 1.0,
                "maxTokens": 4000
            },
            "messages": [
                {"role": "system", "text": SYSTEM_PROMPT},
                {"role": "user", "text": message.text}
            ]
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=60)
        result = response.json()
        
        if 'result' in result:
            answer = result['result']['alternatives'][0]['message']['text']
            if len(answer) > 4000:
                for i in range(0, len(answer), 4000):
                    bot.send_message(message.chat.id, answer[i:i+4000])
            else:
                bot.reply_to(message, answer)
        else:
            bot.reply_to(message, f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}\nПопробуй позже.")

# ========== ЗАПУСК ==========
print("=" * 50)
print("🤖 БОТ ЗАПУЩЕН!")
print("=" * 50)
bot.polling()