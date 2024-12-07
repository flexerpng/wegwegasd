import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler, ContextTypes

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            referrer_id INTEGER,
            join_date TEXT,
            referral_count INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# Генерация реферальной ссылки
def get_referral_link(bot_username: str, user_id: int) -> str:
    return f"https://t.me/{bot_username}?start={user_id}"

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Подключение к БД
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Проверяем, есть ли реферер
    referrer_id = None
    if context.args and context.args[0].isdigit():
        referrer_id = int(context.args[0])
        if referrer_id != user_id:  # Проверка, чтобы пользователь не мог быть своим реферером
            c.execute('SELECT user_id FROM users WHERE user_id = ?', (referrer_id,))
            if c.fetchone():
                # Увеличиваем счетчик рефералов у реферера
                c.execute('UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?', (referrer_id,))
    
    # Проверяем, новый ли пользователь
    c.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    if not c.fetchone():
        c.execute('''
            INSERT INTO users (user_id, username, referrer_id, join_date, referral_count)
            VALUES (?, ?, ?, ?, 0)
        ''', (user_id, username, referrer_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        # Отправляем приветственное сообщение
        welcome_msg = "Добро пожаловать в бота! 👋"
        if referrer_id:
            welcome_msg += "\nВы были приглашены другим пользователем."
    else:
        welcome_msg = "С возвращением! 👋"
    
    conn.commit()
    
    # Создаем реферальную ссылку
    bot = await context.bot.get_me()
    referral_link = get_referral_link(bot.username, user_id)
    
    # Получаем статистику
    c.execute('''
        SELECT referral_count,
               (SELECT COUNT(*) FROM users WHERE referrer_id = ?) as direct_refs
        FROM users WHERE user_id = ?
    ''', (user_id, user_id))
    stats = c.fetchone()
    referral_count = stats[0] if stats else 0
    
    # Создаем клавиатуру
    keyboard = [
        [InlineKeyboardButton("📊 Моя статистика", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ Информация", callback_data="info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"{welcome_msg}\n\n"
        f"🔗 Ваша реферальная ссылка:\n{referral_link}\n\n"
        f"👥 Количество ваших рефералов: {referral_count}",
        reply_markup=reply_markup
    )
    
    conn.close()

# Обработчик кнопок
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    if query.data == "stats":
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('''
            SELECT referral_count,
                   (SELECT COUNT(*) FROM users WHERE referrer_id = ?) as direct_refs
            FROM users WHERE user_id = ?
        ''', (user_id, user_id))
        stats = c.fetchone()
        conn.close()
        
        await query.answer()
        await query.message.reply_text(
            f"📊 Ваша статистика:\n"
            f"👥 Количество рефералов: {stats[0]}\n"
            f"🎯 Прямых приглашений: {stats[1]}"
        )
    
    elif query.data == "info":
        await query.answer()
        await query.message.reply_text(
            "ℹ️ Информация о реферальной системе:\n\n"
            "1. Отправьте свою реферальную ссылку друзьям\n"
            "2. Когда они присоединятся по вашей ссылке, вы получите бонус\n"
            "3. Следите за своей статистикой в разделе 'Моя статистика'"
        )

async def my_refs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Получаем список рефералов
    c.execute('''
        SELECT username, join_date 
        FROM users 
        WHERE referrer_id = ?
        ORDER BY join_date DESC
    ''', (user_id,))
    refs = c.fetchall()
    
    if not refs:
        await update.message.reply_text("У вас пока нет рефералов. Отправьте свою реферальную ссылку друзьям!")
    else:
        refs_text = "Список ваших рефералов:\n\n"
        for i, (username, join_date) in enumerate(refs, 1):
            refs_text += f"{i}. @{username or 'Неизвестно'} (присоединился: {join_date})\n"
        
        await update.message.reply_text(refs_text)
    
    conn.close()

def main():
    # Инициализация базы данных
    init_db()
    
    # Создание приложения
    application = Application.builder().token(TOKEN).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("refs", my_refs))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
