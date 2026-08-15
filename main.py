import os
import telebot
import requests
import json
import time
import hashlib
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ========== КОНФИГ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
FOLDER_ID = os.getenv("FOLDER_ID")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

if not all([BOT_TOKEN, YANDEX_API_KEY, FOLDER_ID, ADMIN_ID]):
    print("❌ ОШИБКА: Не все переменные окружения загружены!")
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# ========== ХРАНИЛИЩА ==========
user_history = {}
user_messages = {}

# ========== ПРОМПТЫ (БЕЗ УПОМИНАНИЙ ЯНДЕКСА) ==========
SYSTEM_PROMPT = """Ты — профессиональный ассистент с искусственным интеллектом.
Твои особенности:
- Отвечаешь максимально подробно и глубоко
- Используешь факты, примеры, структуру
- Помнишь предыдущие сообщения в диалоге
- Адаптируешься под стиль и потребности пользователя

Важно: Всегда отвечай на русском языке, если пользователь не просит иначе.
Никогда не упоминай, на какой платформе или модели ты работаешь. Просто отвечай как ИИ-ассистент."""

PROMPTS = {
    "конспект": "Ты — профессиональный конспектировщик. Сделай структурированный, краткий, но ёмкий конспект с ключевыми мыслями.",
    "код": "Ты — senior-разработчик. Напиши готовый рабочий код с комментариями и объяснениями.",
    "перевод": "Ты — профессиональный лингвист. Переведи текст качественно, литературно и точно.",
    "анализ": "Ты — аналитик данных. Сделай глубокий разбор темы с цифрами, фактами и выводами.",
    "объясни": "Ты — учитель. Объясни сложную тему простыми словами, с примерами из жизни.",
    "напиши": "Ты — профессиональный копирайтер. Напиши качественный, структурированный текст по теме."
}

# ========== КЛАВИАТУРА ==========
def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📚 Конспект"),
        KeyboardButton("💻 Написать код"),
        KeyboardButton("🌍 Перевод"),
        KeyboardButton("🔍 Анализ"),
        KeyboardButton("📖 Объясни"),
        KeyboardButton("✍️ Написать текст"),
        KeyboardButton("🆘 Помощь"),
        KeyboardButton("🗑 Очистить историю")
    )
    return keyboard

def inline_buttons():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📚 Конспект", callback_data="mode_конспект"),
        InlineKeyboardButton("💻 Код", callback_data="mode_код"),
        InlineKeyboardButton("🌍 Перевод", callback_data="mode_перевод"),
        InlineKeyboardButton("🔍 Анализ", callback_data="mode_анализ"),
        InlineKeyboardButton("📖 Объясни", callback_data="mode_объясни"),
        InlineKeyboardButton("✍️ Написать", callback_data="mode_напиши"),
        InlineKeyboardButton("🆘 Помощь", callback_data="help"),
        InlineKeyboardButton("🗑 Очистить", callback_data="clear")
    )
    return keyboard

# ========== ОБРАБОТКА КНОПОК ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    
    if call.data.startswith("mode_"):
        mode = call.data.replace("mode_", "")
        bot.answer_callback_query(call.id, f"✅ Режим: {mode}")
        bot.send_message(call.message.chat.id, 
            f"🔧 **Выбран режим: {mode.upper()}**\n\n"
            f"Отправь текст для обработки в этом режиме.",
            reply_markup=main_keyboard()
        )
        if user_id not in user_history:
            user_history[user_id] = {"history": [], "mode": mode}
        else:
            user_history[user_id]["mode"] = mode
    
    elif call.data == "help":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id,
            "🆘 **Помощь**\n\n"
            "📌 **Как пользоваться ботом:**\n"
            "1. Выбери режим (Конспект, Код, Перевод и т.д.)\n"
            "2. Отправь текст\n"
            "3. Бот обработает и ответит\n\n"
            "❓ **Остались вопросы?**\n"
            "Напиши @FlanSupportBot — мой бот-помощник!\n\n"
            "⚡ **Совет:** Используй меню внизу экрана для быстрого выбора режима."
        )
    
    elif call.data == "clear":
        bot.answer_callback_query(call.id, "🗑 История очищена!")
        if user_id in user_history:
            user_history[user_id]["history"] = []
        bot.send_message(call.message.chat.id, "✅ История диалога очищена!")

# ========== КОМАНДА /START ==========
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id not in user_history:
        user_history[user_id] = {"history": [], "mode": "анализ"}
    
    if user_id == ADMIN_ID:
        bot.reply_to(message, 
            "👑 **Админ-панель**\n\n"
            f"📊 Пользователей: {len(user_messages)}",
            reply_markup=admin_panel()
        )
    else:
        bot.reply_to(message,
            "🤖 **Привет! Я Супер-Бот с искусственным интеллектом!**\n\n"
            "🔥 **Что я умею:**\n"
            "✅ Делать конспекты\n"
            "✅ Писать код\n"
            "✅ Переводить тексты\n"
            "✅ Анализировать данные\n"
            "✅ Объяснять сложное простым языком\n"
            "✅ Помнить контекст диалога\n\n"
            "📌 **Как начать:**\n"
            "1️⃣ Выбери режим в меню внизу\n"
            "2️⃣ Отправь текст\n"
            "3️⃣ Получи качественный ответ!\n\n"
            "🆘 Нужна помощь? Нажми 'Помощь' в меню!",
            reply_markup=main_keyboard()
        )

# ========== ОСНОВНАЯ ЛОГИКА ==========
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    text = message.text
    
    if user_id == ADMIN_ID and not text.startswith('/'):
        bot.reply_to(message, "👑 Админ-панель:", reply_markup=admin_panel())
        return
    
    # Обработка кнопок меню
    if text == "📚 Конспект":
        set_mode(user_id, "конспект")
        bot.reply_to(message, "✅ Режим **Конспект** активирован!\nОтправь текст для конспектирования.")
        return
    elif text == "💻 Написать код":
        set_mode(user_id, "код")
        bot.reply_to(message, "✅ Режим **Код** активирован!\nОпиши, что нужно написать.")
        return
    elif text == "🌍 Перевод":
        set_mode(user_id, "перевод")
        bot.reply_to(message, "✅ Режим **Перевод** активирован!\nОтправь текст для перевода.")
        return
    elif text == "🔍 Анализ":
        set_mode(user_id, "анализ")
        bot.reply_to(message, "✅ Режим **Анализ** активирован!\nОтправь данные для анализа.")
        return
    elif text == "📖 Объясни":
        set_mode(user_id, "объясни")
        bot.reply_to(message, "✅ Режим **Объясни** активирован!\nНапиши тему, которую нужно объяснить.")
        return
    elif text == "✍️ Написать текст":
        set_mode(user_id, "напиши")
        bot.reply_to(message, "✅ Режим **Написать текст** активирован!\nОпиши, что нужно написать.")
        return
    elif text == "🆘 Помощь":
        bot.reply_to(message,
            "🆘 **Бот-помощник**\n\n"
            "❓ Если у тебя возникли вопросы по работе с ботом, "
            "или нужна дополнительная помощь — напиши сюда:\n"
            "👉 @FlanSupportBot\n\n"
            "Это мой бот-помощник, он ответит на все вопросы! 🤖"
        )
        return
    elif text == "🗑 Очистить историю":
        if user_id in user_history:
            user_history[user_id]["history"] = []
        bot.reply_to(message, "🗑 История диалога очищена!")
        return
    
    process_query(message, text)

def set_mode(user_id, mode):
    if user_id not in user_history:
        user_history[user_id] = {"history": [], "mode": mode}
    else:
        user_history[user_id]["mode"] = mode

def process_query(message, query_text):
    user_id = message.from_user.id
    username = message.from_user.username or "без username"
    
    user_messages[user_id] = {
        'user_id': user_id,
        'username': username,
        'last_message': query_text[:100],
        'last_time': time.time()
    }
    
    if user_id not in user_history:
        user_history[user_id] = {"history": [], "mode": "анализ"}
    
    mode = user_history[user_id].get("mode", "анализ")
    
    # Отправляем админу
    try:
        bot.send_message(
            ADMIN_ID,
            f"📩 **Новое сообщение**\n"
            f"👤 @{username}\n"
            f"🆔 ID: {user_id}\n"
            f"📝 {query_text[:300]}\n"
            f"⚡ Режим: {mode}\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}"
        )
    except:
        pass
    
    user_history[user_id]["history"].append({"role": "user", "content": query_text})
    if len(user_history[user_id]["history"]) > 20:
        user_history[user_id]["history"] = user_history[user_id]["history"][-20:]
    
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + PROMPTS.get(mode, "")},
            *user_history[user_id]["history"]
        ]
        
        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        headers = {
            "Authorization": f"Api-Key {YANDEX_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
            "completionOptions": {
                "stream": False,
                "temperature": 0.9,
                "maxTokens": 4000
            },
            "messages": messages
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=120)
        result = response.json()
        
        if 'result' in result:
            answer = result['result']['alternatives'][0]['message']['text']
            user_history[user_id]["history"].append({"role": "assistant", "content": answer})
            
            if len(answer) > 4000:
                for i in range(0, len(answer), 4000):
                    bot.send_message(message.chat.id, answer[i:i+4000])
            else:
                bot.reply_to(message, answer, reply_markup=inline_buttons())
        else:
            bot.reply_to(message, f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}\nПопробуй позже.", reply_markup=main_keyboard())

# ========== АДМИН-ПАНЕЛЬ ==========
def admin_panel():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("👥 Пользователи", callback_data="admin_users"),
        InlineKeyboardButton("📨 Рассылка", callback_data="admin_broadcast"),
        InlineKeyboardButton("⚡ О боте", callback_data="admin_about")
    )
    return keyboard

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_callbacks(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Только для админа!")
        return
    
    if call.data == "admin_stats":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id,
            f"📊 **Статистика**\n\n"
            f"👥 Пользователей: {len(user_messages)}\n"
            f"💾 В памяти: {sum(len(h['history']) for h in user_history.values())} сообщений\n"
            f"⏱ Активных: {len([u for u in user_messages.values() if time.time() - u['last_time'] < 3600])}"
        )
    
    elif call.data == "admin_users":
        bot.answer_callback_query(call.id)
        users_list = "\n".join([f"👤 @{u.get('username', 'без username')}" 
                               for u in list(user_messages.values())[-20:]])
        bot.send_message(call.message.chat.id, f"👥 **Пользователи:**\n\n{users_list}")
    
    elif call.data == "admin_broadcast":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "✏️ Введи текст для рассылки:")
        bot.register_next_step_handler(call.message, send_broadcast)
    
    elif call.data == "admin_about":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id,
            "⚡ **О боте**\n\n"
            "🤖 Мощный ИИ-ассистент\n"
            "🧠 С памятью диалога\n"
            "📚 6 режимов работы\n"
            "⚡ Быстрые ответы\n"
            "🆘 Поддержка @FlanSupportBot"
        )

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

# ========== ЗАПУСК ==========
print("=" * 50)
print("🤖 МЕГА-БОТ ЗАПУЩЕН!")
print(f"👑 Админ ID: {ADMIN_ID}")
print("📚 6 режимов работы")
print("=" * 50)

# Нужно для Render (чтобы он знал, что порт занят, даже если это веб-бот)
if os.getenv("PORT"):
    print(f"✅ Render порт {os.getenv('PORT')} определен")
    
bot.polling(non_stop=True) # Добавил non_stop=True для надежности