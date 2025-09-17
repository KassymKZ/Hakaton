import requests
import telebot
import logging

logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot('7567419832:AAGv0eE9K7bAuOMMzv_F8SskyAb4Qcj-tG0')
ADMIN_GROUP_ID = "-4940285744"  # Замените на реальный ID

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    # Дублируем сообщение пользователя админам
    try:
        user_name = message.from_user.first_name
        if message.from_user.username:
            user_name += f" (@{message.from_user.username})"
        
        admin_msg = f"📩 Входящее от {user_name}:\n{message.text}"
        bot.send_message(ADMIN_GROUP_ID, admin_msg)
    except Exception as e:
        logging.error(f"Ошибка отправки админам: {e}")
    
    # Отправляем запрос в shai.pro
    headers = {
        'Authorization': 'Bearer app-LqQKmr2WcmFUTAjZk2adM46j',
        'Content-Type': 'application/json'
    }
    
    data = {
        'inputs': {},
        'query': message.text,
        'response_mode': 'blocking',
        'user': str(message.from_user.id),
        'conversation_id': f"telegram_{message.chat.id}"
    }
    
    try:
        # Используем найденный API endpoint
        response = requests.post('https://hackathon.shai.pro/api/v1/apps/ODwjlCdBp4b1Bzsh/chat-messages', 
                               json=data, headers=headers)
        
        logging.info(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', 'Ответ получен')
            
            # Отвечаем пользователю
            bot.reply_to(message, answer)
            
            # Дублируем ответ админам
            try:
                bot.send_message(ADMIN_GROUP_ID, f"🤖 Ответ для {user_name}:\n{answer}")
            except:
                pass
        else:
            bot.reply_to(message, "Извините, произошла ошибка")
            
    except Exception as e:
        logging.error(f"Ошибка API: {e}")
        bot.reply_to(message, "Техническая ошибка")

bot.polling()