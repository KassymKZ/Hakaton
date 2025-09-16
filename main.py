import requests
import telebot
import logging

logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot('7567419832:AAGv0eE9K7bAuOMMzv_F8SskyAb4Qcj-tG0')

# ID группы админов (получите через @userinfobot)
ADMIN_GROUP_ID = "-4940285744"  # Замените на реальный ID группы

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    # Дублируем сообщение пользователя админам
    try:
        user_info = f"Пользователь: {message.from_user.first_name}"
        if message.from_user.username:
            user_info += f" (@{message.from_user.username})"
        user_info += f"\nID: {message.from_user.id}"
        
        admin_message = f"Входящее сообщение:\n{user_info}\nТекст: {message.text}"
        bot.send_message(ADMIN_GROUP_ID, admin_message)
    except Exception as e:
        logging.error(f"Ошибка отправки сообщения пользователя админам: {e}")
    
    # Обрабатываем запрос через shai.pro
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
        response = requests.post('https://api.shai.pro/v1/chat-messages', 
                               json=data, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            bot_answer = result.get('answer', 'Ответ получен')
            
            # Отправляем ответ пользователю
            bot.reply_to(message, bot_answer)
            
            # Дублируем ответ бота админам
            try:
                admin_response = f"Ответ бота для {message.from_user.first_name}:\n{bot_answer}"
                bot.send_message(ADMIN_GROUP_ID, admin_response)
            except Exception as e:
                logging.error(f"Ошибка отправки ответа бота админам: {e}")
                
        else:
            error_msg = "Извините, произошла ошибка при обработке запроса"
            bot.reply_to(message, error_msg)
            
            # Уведомляем админов об ошибке
            try:
                admin_error = f"Ошибка API для {message.from_user.first_name}:\nКод: {response.status_code}\nОтвет: {response.text}"
                bot.send_message(ADMIN_GROUP_ID, admin_error)
            except:
                pass
            
    except Exception as e:
        logging.error(f"Общая ошибка: {e}")
        error_msg = "Произошла техническая ошибка"
        bot.reply_to(message, error_msg)
        
        # Уведомляем админов о технической ошибке
        try:
            admin_tech_error = f"Техническая ошибка для {message.from_user.first_name}:\n{str(e)}"
            bot.send_message(ADMIN_GROUP_ID, admin_tech_error)
        except:
            pass

bot.polling()