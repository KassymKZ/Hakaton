import requests
import telebot

bot = telebot.TeleBot('7567419832:AAGv0eE9K7bAuOMMzv_F8SskyAb4Qcj-tG0')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    headers = {
        'Authorization': 'Bearer app-LqQKmr2WcmFUTAjZk2adM46j',
        'Content-Type': 'application/json'
    }
    data = {
        'inputs': {
            'sys.query': message.text,
            'sys.user_id': str(message.from_user.id),
            'sys.conversation_id': f"telegram_{message.chat.id}"
        },
        'response_mode': 'blocking'
    }
    
    # Используйте URL вашего конкретного воркфлоу вместо общего API
    response = requests.post('https://hackathon.shai.pro/app/d31e3f1f-f2fd-41f1-99b6-f4d258f2fc84/workflow', 
                           json=data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        bot.reply_to(message, result.get('data', {}).get('outputs', {}).get('answer', 'Ошибка обработки'))

bot.polling()