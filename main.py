import requests
import telebot
import logging

logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot('7567419832:AAGv0eE9K7bAuOMMzv_F8SskyAb4Qcj-tG0')
ADMIN_GROUP_ID = "-4940285744"

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    # Дублируем сообщение админам
    try:
        admin_msg = f"Сообщение от {message.from_user.first_name}: {message.text}"
        bot.send_message(ADMIN_GROUP_ID, admin_msg)
    except:
        pass
    
    # Пробуем разные endpoints
    endpoints = [
        'https://api.shai.pro/v1/chat-messages',
        'https://hackathon.shai.pro/api/v1/chat-messages',
        'https://hackathon.shai.pro/v1/workflows/runs'
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.post(endpoint, 
                json={'inputs': {'USER': message.text}, 'response_mode': 'blocking'},
                headers={'Authorization': 'Bearer app-LqQKmr2WcmFUTAjZk2adM46j'})
            
            if response.status_code == 200:
                bot.reply_to(message, "Подключение работает!")
                return
        except:
            continue
    
    bot.reply_to(message, "API пока недоступен")

bot.polling()