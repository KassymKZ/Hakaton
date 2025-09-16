import requests
import telebot
import logging

# Настройка логирования для отладки
logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot('7567419832:AAGv0eE9K7bAuOMMzv_F8SskyAb4Qcj-tG0')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        headers = {
            'Authorization': 'Bearer app-LqQKmr2WcmFUTAjZk2adM46j',
            'Content-Type': 'application/json'
        }
        
        # Правильная структура данных для workflow
        data = {
            'inputs': {
                'USER': message.text  # Используем переменную USER из вашего LLM блока
            },
            'response_mode': 'blocking',
            'user': str(message.from_user.id)
        }
        
        # Правильный API endpoint для workflow
        # api_url = 'https://api.shai.pro/v1/workflows/runs'
        # ИЛИ попробуйте:
        api_url = 'https://hackathon.shai.pro/v1/workflows/d31e3f1f-f2fd-41f1-99b6-f4d258f2fc84/runs'
        
        response = requests.post(api_url, json=data, headers=headers)
        
        logging.info(f"Status: {response.status_code}")
        logging.info(f"Response: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            # Путь к ответу может отличаться, проверьте структуру в логах
            answer = result.get('data', {}).get('outputs', {}).get('text', 'Получен ответ, но не могу его извлечь')
            bot.reply_to(message, answer)
        else:
            bot.reply_to(message, f"Ошибка API: {response.status_code}")
            
    except Exception as e:
        logging.error(f"Error: {e}")
        bot.reply_to(message, "Произошла техническая ошибка")

if __name__ == '__main__':
    bot.polling()