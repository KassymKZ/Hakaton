import requests
import telebot

bot = telebot.TeleBot('7567419832:AAGv0eE9K7bAuOMMzv_F8SskyAb4Qcj-tG0')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    # Отправляем запрос к API вашего приложения shai.pro
    headers = {
        'Authorization': 'Bearer app-LqQKmr2WcmFUTAjZk2adM46j',
        'Content-Type': 'application/json'
    }
    data = {
        'inputs': {},
        'query': message.text,
        'response_mode': 'blocking',
        'user': str(message.from_user.id)
    }
    
    response = requests.post('https://api.shai.pro/v1/chat-messages', 
                           json=data, headers=headers)
    if response.status_code == 200:
        bot.reply_to(message, response.json()['answer'])

bot.polling()