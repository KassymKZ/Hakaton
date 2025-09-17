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
        admin_msg = f"Входящее от {user_name}: {message.text}"
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
        response = requests.post('https://hackathon.shai.pro/api/v1/apps/ODwjlCdBp4b1Bzsh/chat-messages', 
                               json=data, headers=headers, timeout=30)
        
        # Подробная диагностика
        logging.info(f"Status Code: {response.status_code}")
        logging.info(f"Response Headers: {response.headers}")
        logging.info(f"Response Text: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', str(result))
            bot.reply_to(message, answer)
            
            # Дублируем ответ админам
            try:
                bot.send_message(ADMIN_GROUP_ID, f"Ответ: {answer}")
            except:
                pass
        else:
            error_msg = f"Ошибка API: {response.status_code}"
            bot.reply_to(message, error_msg)
            
            # Отправляем детали ошибки админам
            try:
                bot.send_message(ADMIN_GROUP_ID, f"Ошибка API: {response.status_code}\n{response.text}")
            except:
                pass
            
    except Exception as e:
        logging.error(f"Исключение: {e}")
        bot.reply_to(message, f"Техническая ошибка: {str(e)}")

print("Бот запускается...")
bot.polling()