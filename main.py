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
        bot.send_message(ADMIN_GROUP_ID, f"Входящее от {message.from_user.first_name}: {message.text}")
    except:
        pass
    
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
    
    # Попробуйте эти endpoints по очереди:
    endpoints = [
        'https://api.shai.pro/v1/chat-messages',
        'https://hackathon.shai.pro/v1/chat-messages', 
        'https://hackathon.shai.pro/api/v1/chat-messages',
        f'https://hackathon.shai.pro/v1/apps/ODwjlCdBp4b1Bzsh/chat-messages',
        f'https://hackathon.shai.pro/api/v1/workflows/runs'
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.post(endpoint, json=data, headers=headers, timeout=10)
            
            bot.send_message(ADMIN_GROUP_ID, f"Попытка: {endpoint}\nСтатус: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('answer', str(result))
                bot.reply_to(message, answer)
                bot.send_message(ADMIN_GROUP_ID, f"✅ Работает: {endpoint}")
                return
                
        except Exception as e:
            bot.send_message(ADMIN_GROUP_ID, f"Ошибка {endpoint}: {str(e)}")
    
    bot.reply_to(message, "API недоступен")

bot.polling()