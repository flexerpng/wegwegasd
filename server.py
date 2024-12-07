from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
import json
import os

app = Flask(__name__)
CORS(app)

# Инициализация бота
BOT_TOKEN = "7631177027:AAHNS_eJoPBhTsqgyiTxEZconw6QC1J37dY"
bot = telebot.TeleBot(BOT_TOKEN)

# Файл для хранения данных о рефералах
REFERRALS_FILE = 'referrals.json'

def load_referrals():
    if os.path.exists(REFERRALS_FILE):
        with open(REFERRALS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_referrals(referrals):
    with open(REFERRALS_FILE, 'w') as f:
        json.dump(referrals, f)

# Обработка команды start с реферальным кодом
@bot.message_handler(commands=['start'])
def start(message):
    args = message.text.split()
    if len(args) > 1 and args[1].startswith('ref'):
        referrer_id = args[1][3:]  # Получаем ID реферера
        user_id = str(message.from_user.id)
        
        referrals = load_referrals()
        
        # Проверяем, не является ли пользователь уже чьим-то рефералом
        is_already_referral = False
        for ref_list in referrals.values():
            if user_id in ref_list:
                is_already_referral = True
                break
        
        if not is_already_referral and user_id != referrer_id:
            if referrer_id not in referrals:
                referrals[referrer_id] = []
            if user_id not in referrals[referrer_id]:
                referrals[referrer_id].append(user_id)
                save_referrals(referrals)
                bot.reply_to(message, "Вы успешно присоединились по реферальной ссылке!")
            else:
                bot.reply_to(message, "Вы уже являетесь рефералом этого пользователя!")
        else:
            bot.reply_to(message, "Добро пожаловать в игру!")
    else:
        bot.reply_to(message, "Добро пожаловать в игру!")

# API эндпоинт для получения статистики рефералов
@app.route('/api/referrals/<user_id>', methods=['GET'])
def get_referral_stats(user_id):
    referrals = load_referrals()
    user_referrals = referrals.get(user_id, [])
    return jsonify({
        'count': len(user_referrals),
        'bonus': len(user_referrals) * 0.1  # 10% бонус за каждого реферала
    })

if __name__ == '__main__':
    # Запускаем бота в отдельном потоке
    import threading
    bot_thread = threading.Thread(target=bot.polling, daemon=True)
    bot_thread.start()
    
    # Запускаем Flask сервер
    app.run(port=5000)
