import requests
import telebot
from telebot import types
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)

bot = telebot.TeleBot('7567419832:AAGv0eE9K7bAuOMMzv_F8SskyAb4Qcj-tG0')
ADMIN_GROUP_ID = "-4940285744"
ADMIN_IDS = [824360574]

# Хранение состояний пользователей
user_states = {}
user_profiles = {}

class UserState:
    LANGUAGE = "language"
    AGE = "age"
    GENDER = "gender"
    BIRTHPLACE = "birthplace"
    FAMILY = "family"
    COURSE = "course"
    SPECIALTY = "specialty"
    HOUSING = "housing"
    COMPLETED = "completed"

def create_language_menu():
    """Меню выбора языка с эмодзи"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🇰🇿 Қазақша", callback_data="lang_kz"))
    markup.add(types.InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"))
    markup.add(types.InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"))
    return markup

def create_gender_menu(language):
    """Меню выбора пола"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    if language == "kz":
        markup.add(
            types.InlineKeyboardButton("👨 Ер", callback_data="gender_male"),
            types.InlineKeyboardButton("👩 Әйел", callback_data="gender_female")
        )
    elif language == "en":
        markup.add(
            types.InlineKeyboardButton("👨 Male", callback_data="gender_male"),
            types.InlineKeyboardButton("👩 Female", callback_data="gender_female")
        )
    else:
        markup.add(
            types.InlineKeyboardButton("👨 Мужской", callback_data="gender_male"),
            types.InlineKeyboardButton("👩 Женский", callback_data="gender_female")
        )
    return markup

def create_birthplace_menu(language):
    """Меню выбора места рождения"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    regions = [
        ("🏛️ Город Астана", "astana"),
        ("🌆 Город Алма-Ата", "almaty"),
        ("🏙️ Город Шымкент", "shymkent"),
        ("🌾 Абайская область", "abai"),
        ("🌱 Акмолинская область", "akmola"),
        ("⚡ Актюбинская область", "aktobe"),
        ("🍎 Алматинская область", "almaty_region"),
        ("🛢️ Атырауская область", "atyrau"),
        ("🏔️ Восточно-Казахстанская область", "east_kz"),
        ("🌿 Жамбылская область", "zhambyl"),
        ("🍇 Жетысуская область", "jetysu"),
        ("🌾 Западно-Казахстанская область", "west_kz"),
        ("⚒️ Карагандинская область", "karaganda"),
        ("🌾 Костанайская область", "kostanay"),
        ("🏜️ Кызылординская область", "kyzylorda"),
        ("🌊 Мангистауская область", "mangistau"),
        ("🏭 Павлодарская область", "pavlodar"),
        ("❄️ Северо-Казахстанская область", "north_kz"),
        ("🕌 Туркестанская область", "turkestan"),
        ("⛰️ Улытауская область", "ulytau")
    ]
    
    for text, callback_data in regions:
        markup.add(types.InlineKeyboardButton(text, callback_data=f"birthplace_{callback_data}"))
    
    return markup

def create_family_menu(language):
    """Меню семейного статуса"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if language == "kz":
        markup.add(types.InlineKeyboardButton("👨‍👩‍👧‍👦 Толық отбасы", callback_data="family_full"))
        markup.add(types.InlineKeyboardButton("💔 Толық емес отбасы", callback_data="family_incomplete"))
        markup.add(types.InlineKeyboardButton("😔 Жетім", callback_data="family_orphan"))
    elif language == "en":
        markup.add(types.InlineKeyboardButton("👨‍👩‍👧‍👦 Complete family", callback_data="family_full"))
        markup.add(types.InlineKeyboardButton("💔 Incomplete family", callback_data="family_incomplete"))
        markup.add(types.InlineKeyboardButton("😔 Orphan", callback_data="family_orphan"))
    else:
        markup.add(types.InlineKeyboardButton("👨‍👩‍👧‍👦 Полная", callback_data="family_full"))
        markup.add(types.InlineKeyboardButton("💔 Неполная", callback_data="family_incomplete"))
        markup.add(types.InlineKeyboardButton("😔 Сирота", callback_data="family_orphan"))
    return markup

def create_course_menu(language):
    """Меню курса обучения"""
    markup = types.InlineKeyboardMarkup(row_width=4)
    markup.add(
        types.InlineKeyboardButton("1️⃣ 1 курс", callback_data="course_1"),
        types.InlineKeyboardButton("2️⃣ 2 курс", callback_data="course_2"),
        types.InlineKeyboardButton("3️⃣ 3 курс", callback_data="course_3"),
        types.InlineKeyboardButton("4️⃣ 4 курс", callback_data="course_4")
    )
    return markup

def create_housing_menu(language):
    """Меню типа жилья"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    if language == "kz":
        markup.add(types.InlineKeyboardButton("🏠 Жатақхана", callback_data="housing_dormitory"))
        markup.add(types.InlineKeyboardButton("🏡 Жалдау", callback_data="housing_rent"))
        markup.add(types.InlineKeyboardButton("🏘️ Меншікті үй (туыстарда)", callback_data="housing_own"))
    elif language == "en":
        markup.add(types.InlineKeyboardButton("🏠 Dormitory", callback_data="housing_dormitory"))
        markup.add(types.InlineKeyboardButton("🏡 Rental", callback_data="housing_rent"))
        markup.add(types.InlineKeyboardButton("🏘️ Own housing (relatives)", callback_data="housing_own"))
    else:
        markup.add(types.InlineKeyboardButton("🏠 Общежитие", callback_data="housing_dormitory"))
        markup.add(types.InlineKeyboardButton("🏡 Аренда жилья", callback_data="housing_rent"))
        markup.add(types.InlineKeyboardButton("🏘️ Собственное жилье (у родственников)", callback_data="housing_own"))
    return markup

def create_category_menu(language):
    """Меню категорий проблем"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    categories = {
        'kz': [
            ("💰 Қаржылық мәселелер", "finance"),
            ("📚 Оқу қиындықтары", "study"),
            ("😰 Әлеуметтік қорқыныштар", "social"),
            ("👨‍👩‍👧‍👦 Отбасы және орта", "family"),
            ("🏠 Тұрмыстық мәселелер", "household"),
            ("🎯 Мамандық таңдау", "career")
        ],
        'ru': [
            ("💰 Финансовые проблемы", "finance"),
            ("📚 Учебные трудности", "study"),
            ("😰 Социальные страхи", "social"),
            ("👨‍👩‍👧‍👦 Семья и окружение", "family"),
            ("🏠 Бытовые проблемы", "household"),
            ("🎯 Профориентация", "career")
        ],
        'en': [
            ("💰 Financial problems", "finance"),
            ("📚 Academic difficulties", "study"),
            ("😰 Social fears", "social"),
            ("👨‍👩‍👧‍👦 Family and environment", "family"),
            ("🏠 Household problems", "household"),
            ("🎯 Career guidance", "career")
        ]
    }
    
    for text, callback_data in categories[language]:
        markup.add(types.InlineKeyboardButton(text, callback_data=f"{callback_data}_{language}"))
    
    return markup

def get_text(language, key):
    """Получить текст на нужном языке с эмодзи"""
    texts = {
        'language_select': {
            'kz': '🌐 Тілді таңдаңыз:',
            'ru': '🌐 Выберите язык:',
            'en': '🌐 Choose language:'
        },
        'age_request': {
            'kz': '🎂 Жасыңызды жазыңыз (тек цифрлар):',
            'ru': '🎂 Введите ваш возраст (только цифры):',
            'en': '🎂 Enter your age (numbers only):'
        },
        'gender_request': {
            'kz': '⚧️ Жынысыңызды таңдаңыз:',
            'ru': '⚧️ Выберите ваш пол:',
            'en': '⚧️ Choose your gender:'
        },
        'birthplace_request': {
            'kz': '🏙️ Туған жеріңізді таңдаңыз:',
            'ru': '🏙️ Выберите место рождения:',
            'en': '🏙️ Choose your birthplace:'
        },
        'family_request': {
            'kz': '👨‍👩‍👧‍👦 Отбасылық жағдайыңызды таңдаңыз:',
            'ru': '👨‍👩‍👧‍👦 Выберите семейное положение:',
            'en': '👨‍👩‍👧‍👦 Choose your family status:'
        },
        'course_request': {
            'kz': '📚 Курсыңызды таңдаңыз:',
            'ru': '📚 Выберите курс обучения:',
            'en': '📚 Choose your year of study:'
        },
        'specialty_request': {
            'kz': '🎓 Мамандығыңызды жазыңыз:',
            'ru': '🎓 Введите вашу специальность:',
            'en': '🎓 Enter your specialty:'
        },
        'housing_request': {
            'kz': '🏠 Тұрғылықты жеріңізді таңдаңыз:',
            'ru': '🏠 Выберите тип жилья:',
            'en': '🏠 Choose your housing type:'
        },
        'profile_complete': {
            'kz': '✅ Профиль толтырылды! Категорияны таңдаңыз:',
            'ru': '✅ Профиль заполнен! Выберите категорию:',
            'en': '✅ Profile completed! Choose category:'
        },
        'age_invalid': {
            'kz': '❌ Жасыңызды дұрыс енгізіңіз (18-30 арасында):',
            'ru': '❌ Пожалуйста, введите корректный возраст (18-30):',
            'en': '❌ Please enter a valid age (18-30):'
        }
    }
    
    return texts.get(key, {}).get(language, texts.get(key, {}).get('en', ''))

@bot.message_handler(commands=['start'])
def start_command(message):
    """Начало анкетирования с выбора языка"""
    user_states[message.from_user.id] = UserState.LANGUAGE
    user_profiles[message.from_user.id] = {
        'telegram_id': message.from_user.id,
        'telegram_username': message.from_user.username or "",
        'telegram_first_name': message.from_user.first_name or "",
        'telegram_last_name': message.from_user.last_name or "",
        'registration_date': datetime.now().isoformat()
    }
    
    markup = create_language_menu()
    bot.reply_to(message, get_text('en', 'language_select'), reply_markup=markup)

# Обработчики выбора языка
@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def handle_language_selection(call):
    bot.answer_callback_query(call.id)
    
    language = call.data.split('_')[1]
    user_profiles[call.from_user.id]['user_language'] = language
    user_states[call.from_user.id] = UserState.AGE
    
    bot.edit_message_text(
        get_text(language, 'age_request'),
        call.message.chat.id,
        call.message.message_id
    )

# Обработчики выбора пола
@bot.callback_query_handler(func=lambda call: call.data.startswith('gender_'))
def handle_gender_selection(call):
    bot.answer_callback_query(call.id)
    
    gender = call.data.split('_')[1]
    language = user_profiles[call.from_user.id]['user_language']
    
    user_profiles[call.from_user.id]['user_gender'] = gender
    user_states[call.from_user.id] = UserState.BIRTHPLACE
    
    markup = create_birthplace_menu(language)
    bot.edit_message_text(
        get_text(language, 'birthplace_request'),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

# Обработчики выбора места рождения
@bot.callback_query_handler(func=lambda call: call.data.startswith('birthplace_'))
def handle_birthplace_selection(call):
    bot.answer_callback_query(call.id)
    
    birthplace = call.data.split('_')[1]
    language = user_profiles[call.from_user.id]['user_language']
    
    user_profiles[call.from_user.id]['user_birthplace'] = birthplace
    user_states[call.from_user.id] = UserState.FAMILY
    
    markup = create_family_menu(language)
    bot.edit_message_text(
        get_text(language, 'family_request'),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

# Обработчики семейного статуса
@bot.callback_query_handler(func=lambda call: call.data.startswith('family_'))
def handle_family_selection(call):
    bot.answer_callback_query(call.id)
    
    family = call.data.split('_')[1]
    language = user_profiles[call.from_user.id]['user_language']
    
    user_profiles[call.from_user.id]['user_family_status'] = family
    user_states[call.from_user.id] = UserState.COURSE
    
    markup = create_course_menu(language)
    bot.edit_message_text(
        get_text(language, 'course_request'),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

# Обработчики курса
@bot.callback_query_handler(func=lambda call: call.data.startswith('course_'))
def handle_course_selection(call):
    bot.answer_callback_query(call.id)
    
    course = call.data.split('_')[1]
    language = user_profiles[call.from_user.id]['user_language']
    
    user_profiles[call.from_user.id]['user_course'] = int(course)
    user_states[call.from_user.id] = UserState.SPECIALTY
    
    bot.edit_message_text(
        get_text(language, 'specialty_request'),
        call.message.chat.id,
        call.message.message_id
    )

# Обработчики жилья
@bot.callback_query_handler(func=lambda call: call.data.startswith('housing_'))
def handle_housing_selection(call):
    bot.answer_callback_query(call.id)
    
    housing = call.data.split('_')[1]
    language = user_profiles[call.from_user.id]['user_language']
    
    user_profiles[call.from_user.id]['user_housing_type'] = housing
    user_states[call.from_user.id] = UserState.COMPLETED
    
    # Отправляем профиль в админскую группу
    send_profile_to_admin(user_profiles[call.from_user.id])
    
    # Показываем меню категорий
    markup = create_category_menu(language)
    bot.edit_message_text(
        get_text(language, 'profile_complete'),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Обработка текстовых сообщений"""
    user_id = message.from_user.id
    
    if user_id not in user_states:
        start_command(message)
        return
    
    state = user_states[user_id]
    language = user_profiles.get(user_id, {}).get('user_language', 'ru')
    
    if state == UserState.AGE:
        try:
            age = int(message.text)
            if 16 <= age <= 35:  # Разумные пределы для студентов
                user_profiles[user_id]['user_age'] = age
                user_states[user_id] = UserState.GENDER
                markup = create_gender_menu(language)
                bot.reply_to(message, get_text(language, 'gender_request'), reply_markup=markup)
            else:
                bot.reply_to(message, get_text(language, 'age_invalid'))
        except ValueError:
            bot.reply_to(message, get_text(language, 'age_invalid'))
            
    elif state == UserState.SPECIALTY:
        user_profiles[user_id]['user_specialty'] = message.text
        user_states[user_id] = UserState.HOUSING
        markup = create_housing_menu(language)
        bot.reply_to(message, get_text(language, 'housing_request'), reply_markup=markup)

def send_profile_to_admin(profile):
    """Отправка профиля в админскую группу"""
    try:
        region_names = {
            'astana': 'Город Астана',
            'almaty': 'Город Алма-Ата',
            'shymkent': 'Город Шымкент',
            'abai': 'Абайская область',
            'akmola': 'Акмолинская область',
            'aktobe': 'Актюбинская область',
            'almaty_region': 'Алматинская область',
            'atyrau': 'Атырауская область',
            'east_kz': 'Восточно-Казахстанская область',
            'zhambyl': 'Жамбылская область',
            'jetysu': 'Жетысуская область',
            'west_kz': 'Западно-Казахстанская область',
            'karaganda': 'Карагандинская область',
            'kostanay': 'Костанайская область',
            'kyzylorda': 'Кызылординская область',
            'mangistau': 'Мангистауская область',
            'pavlodar': 'Павлодарская область',
            'north_kz': 'Северо-Казахстанская область',
            'turkestan': 'Туркестанская область',
            'ulytau': 'Улытауская область'
        }
        
        family_names = {
            'full': '👨‍👩‍👧‍👦 Полная семья',
            'incomplete': '💔 Неполная семья',
            'orphan': '😔 Сирота'
        }
        
        gender_names = {
            'male': '👨 Мужской',
            'female': '👩 Женский'
        }
        
        housing_names = {
            'dormitory': '🏠 Общежитие',
            'rent': '🏡 Аренда жилья',
            'own': '🏘️ Собственное жилье (у родственников)'
        }
        
        report = f"""
📋 НОВЫЙ СТУДЕНТ ЗАРЕГИСТРИРОВАН

🆔 Telegram ID: {profile.get('telegram_id')}
📞 Username: @{profile.get('telegram_username', 'не указан')}
👤 Имя в Telegram: {profile.get('telegram_first_name', '')} {profile.get('telegram_last_name', '')}
🎂 Возраст: {profile.get('user_age')}
⚧️ Пол: {gender_names.get(profile.get('user_gender'), 'Не указано')}
🏙️ Место рождения: {region_names.get(profile.get('user_birthplace'), 'Не указано')}
👨‍👩‍👧‍👦 Семья: {family_names.get(profile.get('user_family_status'), 'Не указано')}
📚 Курс: {profile.get('user_course')} курс
🎓 Специальность: {profile.get('user_specialty')}
🏠 Жилье: {housing_names.get(profile.get('user_housing_type'), 'Не указано')}
🌐 Язык: {profile.get('user_language', 'ru').upper()}
🕐 Время регистрации: {datetime.now().strftime("%d.%m.%Y %H:%M")}

━━━━━━━━━━━━━━━━━━
"""
        
        bot.send_message(ADMIN_GROUP_ID, report)
        
    except Exception as e:
        logging.error(f"Ошибка отправки профиля админам: {e}")

bot.polling()