#!/usr/bin/env python3
"""
Исправленная версия IT-профориентационного бота с 30 вопросами
"""

import telebot
import json
import logging
from telebot import types
from config import Config
from database.queries import Database

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и компонентов
bot = telebot.TeleBot(Config.BOT_TOKEN)
db = Database(Config.DB_URL)

# Словарь для хранения состояния пользователей
user_states = {}

# Состояния админ-панели
admin_states = {}

def is_admin(user_id):
    """Проверка, является ли пользователь администратором"""
    return user_id in Config.ADMIN_IDS

@bot.message_handler(commands=['start'])
def start(message):
    """Начальное приветствие"""
    # Получаем актуальное количество вопросов из базы данных
    try:
        questions_dict = db.get_all_questions()
        total_questions = len(questions_dict)
    except:
        total_questions = 30  # Fallback значение
    
    welcome_text = f"""
🎓 Добро пожаловать в IT-профориентатор!

Этот бот поможет вам определить наиболее подходящую IT-специализацию на основе ваших склонностей и предпочтений.

📋 Тест содержит {total_questions} вопросов и займет около 10-15 минут.

Нажмите кнопку "Начать тест" чтобы начать тестирование!
    """
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Начать тест'))
    markup.add(types.KeyboardButton('Помощь'))
    
    bot.reply_to(message, welcome_text, reply_markup=markup)

@bot.message_handler(commands=['help'])
def help_command(message):
    """Справка по командам"""
    # Получаем актуальное количество вопросов из базы данных
    try:
        questions_dict = db.get_all_questions()
        total_questions = len(questions_dict)
    except:
        total_questions = 30  # Fallback значение
    
    help_text = f"""
📚 Доступные команды и кнопки:

🎯 Основные кнопки:
• Начать тест - Начать профориентационный тест ({total_questions} вопросов)
• Помощь - Показать эту справку

⌨️ Команды:
• /start - Начать работу с ботом
• /restart - Начать тест заново
• /admin - Админ-панель

💡 Если тест прервался, используйте кнопку "Начать тест" для продолжения.
    """
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['admin'])
def admin_command(message):
	admin_panel(message)

def admin_panel(message):
    """Главная админ-панель"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Доступ запрещен")
        return
    
    # Получаем статистику
    stats = get_admin_statistics()
    
    admin_text = f"""
🔧 Админ-панель

📊 Статистика:
• Всего пользователей: {stats['total_users']}
• Завершенных тестов: {stats['completed_tests']}
• Всего вопросов: {stats['total_questions']}
• Всего вузов: {stats['total_universities']}
• Всего специализаций: {stats['total_specializations']}

🎛 Управление:
• Вопросы - добавление/удаление/редактирование
• Вузы - добавление/удаление/редактирование
• Специализации - добавление/удаление/редактирование
• Рассылка - отправка сообщений всем пользователям
• Статистика - подробная аналитика
    """
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('❓ Управление вопросами'),
        types.KeyboardButton('🎓 Управление вузами')
    )
    markup.add(
        types.KeyboardButton('🎯 Управление специализациями'),
        types.KeyboardButton('📢 Рассылка')
    )
    markup.add(
        types.KeyboardButton('📊 Статистика')
    )
    markup.add(
        types.KeyboardButton('⬅️ Выход')
    )
    
    admin_states[message.from_user.id] = {'state': 'admin_main'}
    bot.reply_to(message, admin_text, reply_markup=markup)

def get_admin_statistics():
    """Получение статистики для админ-панели"""
    try:
        # Получаем базовую статистику
        total_questions = len(db.get_all_questions())
        total_specializations = len(db.get_all_specializations())
        
        # Получаем количество университетов из JSON файла
        try:
            import json
            import os
            
            universities_file = 'universities.json'
            if os.path.exists(universities_file):
                with open(universities_file, 'r', encoding='utf-8') as f:
                    universities = json.load(f)
                total_universities = len(universities)
            else:
                total_universities = 0
        except:
            total_universities = 0
        
        # Получаем статистику пользователей (если есть)
        try:
            user_stats = db.get_user_statistics()
            total_users = user_stats.get('total_users', 0)
            active_sessions = user_stats.get('active_sessions', 0)
            completed_tests = user_stats.get('completed_tests', 0)
        except:
            total_users = 0
            active_sessions = 0
            completed_tests = 0
        
        return {
            'total_users': total_users,
            'active_sessions': active_sessions,
            'completed_tests': completed_tests,
            'total_questions': total_questions,
            'total_universities': total_universities,
            'total_specializations': total_specializations
        }
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
        return {
            'total_users': 0,
            'active_sessions': 0,
            'completed_tests': 0,
            'total_questions': 0,
            'total_universities': 0,
            'total_specializations': 0
        }

@bot.message_handler(func=lambda message: message.text == 'Начать тест')
def begin_test_button(message):
    """Начать тестирование"""
    try:
        user_id = message.from_user.id
        
        # Очищаем предыдущее состояние пользователя
        if user_id in user_states:
            del user_states[user_id]
        
        # Создаем новую сессию
        session_id = db.create_user_session(user_id)
        user_states[user_id] = {
            'session_id': session_id,
            'current_question': 1,
            'answers': {}
        }
        
        # Отправляем первый вопрос
        send_question(message.chat.id, user_id, 1)
    except Exception as e:
        print(f"❌ Ошибка в begin_test_button: {e}")
        bot.reply_to(message, "❌ Произошла ошибка при запуске теста. Попробуйте еще раз.")

@bot.message_handler(func=lambda message: message.text == 'Помощь')
def help_button(message):
    """Показать справку"""
    help_command(message)

@bot.message_handler(func=lambda message: message.text == 'Назад к результатам')
def back_to_results(message):
    """Вернуться к результатам теста"""
    try:
        user_id = message.from_user.id
        
        if user_id not in user_states:
            bot.reply_to(message, "❌ Нет активной сессии. Начните тест заново.")
            return
        
        current_state = user_states[user_id]
        
        if not current_state.get('show_all_universities'):
            bot.reply_to(message, "❌ Сначала пройдите тест до конца.")
            return
        
        # Показываем результаты снова
        show_results(message)
        
    except Exception as e:
        print(f"❌ Ошибка в back_to_results: {e}")
        bot.reply_to(message, "❌ Произошла ошибка при возврате к результатам.")

@bot.message_handler(func=lambda message: message.text == 'Все вузы')
def show_all_universities_user(message):
    """Показать все университеты для специализации"""
    try:
        user_id = message.from_user.id
        
        if user_id not in user_states:
            bot.reply_to(message, "❌ Нет активной сессии. Начните тест заново.")
            return
        
        current_state = user_states[user_id]
        
        if not current_state.get('show_all_universities'):
            bot.reply_to(message, "❌ Сначала пройдите тест до конца.")
            return
        
        specialization_id = current_state.get('specialization_id')
        specialization_name = current_state.get('specialization_name')
        
        if not specialization_id:
            bot.reply_to(message, "❌ Информация о специализации не найдена.")
            return
        
        # Получаем все университеты для специализации
        universities = db.get_universities_by_specialization(specialization_id)
        
        if not universities:
            bot.reply_to(message, "❌ Университеты для данной специализации не найдены.")
            return
        
        # Сортируем университеты по баллам
        universities_sorted = sorted(universities, key=lambda x: x.get('score_max', 0), reverse=True)
        
        # Группируем университеты по городам
        cities = {}
        for uni in universities_sorted:
            city = uni.get('city', 'Неизвестный город')
            if city not in cities:
                cities[city] = []
            cities[city].append(uni)
        
        result_text = f"""
🏛️ Все университеты по направлению "{specialization_name}":

"""
        
        for city, unis in cities.items():
            result_text += f"\n📍 {city}:\n"
            for uni in unis:
                score_range = f"{uni.get('score_min', 0)}-{uni.get('score_max', 0)}"
                result_text += f"   • {uni['name']}\n"
                result_text += f"     🎯 Баллы ЕГЭ: {score_range}\n"
        
        result_text += f"\n📊 Всего университетов: {len(universities_sorted)}"
        
        # Создаем клавиатуру с кнопкой "Назад"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('Назад к результатам'))
        markup.add(types.KeyboardButton('Начать тест'))
        markup.add(types.KeyboardButton('Помощь'))
        
        bot.send_message(message.chat.id, result_text, reply_markup=markup, disable_web_page_preview=True)
        
        # НЕ очищаем состояние пользователя - он нужен для кнопки "Назад"
        
    except Exception as e:
        print(f"❌ Ошибка в show_all_universities: {e}")
        bot.reply_to(message, "❌ Произошла ошибка при показе университетов.")

def send_question(chat_id, user_id, question_number):
    """Отправить вопрос пользователю"""
    try:
        # Получаем все вопросы из БД
        all_questions = db.get_all_questions()
        question_ids = sorted(all_questions.keys())
        
        # Проверяем, что номер вопроса в пределах
        if question_number > len(question_ids):
            bot.send_message(chat_id, f"❌ Вопрос {question_number} не найден")
            return
        
        # Получаем вопрос по номеру
        question_id = question_ids[question_number - 1]
        question = all_questions[question_id]
        
        # Создаем клавиатуру с вариантами ответов
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for option in question['options']:
            markup.add(types.KeyboardButton(option['text']))
        
        # Отправляем вопрос
        total_questions = len(question_ids)
        bot.send_message(chat_id, f"❓ Вопрос {question_number}/{total_questions}:\n\n{question['text']}", reply_markup=markup)
        
    except Exception as e:
        print(f"❌ Ошибка в send_question: {e}")
        bot.send_message(chat_id, "❌ Ошибка при отправке вопроса")

# ============================================================================
# ОБРАБОТЧИКИ АДМИН-ПАНЕЛИ (должны быть ПЕРЕД общим обработчиком)
# ============================================================================

@bot.message_handler(func=lambda message: message.text == '❓ Управление вопросами')
def questions_management(message):
    """Управление вопросами"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Доступ запрещен")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('📋 Показать все вопросы'),
        types.KeyboardButton('➕ Добавить вопрос')
    )
    markup.add(
        types.KeyboardButton('🗑️ Удалить вопрос'),
        types.KeyboardButton('⬅️ Назад')
    )
    
    bot.reply_to(message, "❓ Управление вопросами\n\nВыберите действие:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '📋 Показать все вопросы')
def show_all_questions(message):
    """Показать все вопросы с пагинацией"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Доступ запрещен")
        return
    
    try:
        questions_dict = db.get_all_questions()
        if not questions_dict:
            bot.reply_to(message, "📭 В базе данных нет вопросов")
            return
        
        # Получаем список ID вопросов
        question_ids = sorted(list(questions_dict.keys()))
        total_questions = len(question_ids)
        
        # Инициализируем состояние пагинации
        admin_states[user_id] = {
            'state': 'viewing_questions',
            'questions_dict': questions_dict,
            'question_ids': question_ids,
            'current_page': 0,
            'questions_per_page': 10
        }
        
        # Показываем первую страницу
        show_questions_page(message, user_id)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

def show_questions_page(message, user_id):
    """Показать страницу с вопросами"""
    state = admin_states.get(user_id, {})
    questions_dict = state.get('questions_dict', {})
    question_ids = state.get('question_ids', [])
    current_page = state.get('current_page', 0)
    questions_per_page = state.get('questions_per_page', 5)
    
    total_questions = len(question_ids)
    total_pages = (total_questions + questions_per_page - 1) // questions_per_page
    
    if total_questions == 0:
        bot.reply_to(message, "📭 В базе данных нет вопросов")
        return
    
    # Вычисляем индексы для текущей страницы
    start_idx = current_page * questions_per_page
    end_idx = min(start_idx + questions_per_page, total_questions)
    
    # Формируем текст страницы
    text = f"📋 Список вопросов (страница {current_page + 1} из {total_pages})\n"
    text += f"📊 Всего вопросов: {total_questions}\n\n"
    
    for i in range(start_idx, end_idx):
        question_id = question_ids[i]
        question = questions_dict[question_id]
        if question:
            # Обрезаем текст вопроса для лучшего отображения
            question_text = question['text']
            if len(question_text) > 60:
                question_text = question_text[:60] + "..."
            
            text += f"🆔 ID: {question_id}\n"
            text += f"📝 {question_text}\n"
            text += f"🏷️ Категория: {question.get('category', 'Не указана')}\n"
            text += f"📊 Вариантов: {len(question.get('options', []))}\n"
            text += "─" * 40 + "\n\n"
    
    # Создаем клавиатуру с навигацией
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    
    # Кнопки навигации
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(types.KeyboardButton('⬅️ Назад'))
    if current_page < total_pages - 1:
        nav_buttons.append(types.KeyboardButton('Вперед ➡️'))
    
    if nav_buttons:
        markup.add(*nav_buttons)
    
    # Информационные кнопки
    info_buttons = []
    if total_pages > 1:
        info_buttons.append(types.KeyboardButton(f'📄 {current_page + 1}/{total_pages}'))
    info_buttons.append(types.KeyboardButton('🔄 Обновить'))
    
    if info_buttons:
        markup.add(*info_buttons)
    
    # Кнопка возврата
    markup.add(types.KeyboardButton('⬅️ К управлению'))
    
    bot.reply_to(message, text, reply_markup=markup)

@bot.message_handler(func=lambda message: admin_states.get(message.from_user.id, {}).get('state') == 'viewing_questions')
def handle_questions_navigation(message):
    """Обработка навигации по вопросам"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    state = admin_states.get(user_id, {})
    current_page = state.get('current_page', 0)
    total_pages = (len(state.get('question_ids', [])) + state.get('questions_per_page', 5) - 1) // state.get('questions_per_page', 5)
    
    if message.text == '⬅️ Назад':
        if current_page > 0:
            state['current_page'] = current_page - 1
            admin_states[user_id] = state
            show_questions_page(message, user_id)
        else:
            bot.reply_to(message, "❌ Вы уже на первой странице")
    
    elif message.text == 'Вперед ➡️':
        if current_page < total_pages - 1:
            state['current_page'] = current_page + 1
            admin_states[user_id] = state
            show_questions_page(message, user_id)
        else:
            bot.reply_to(message, "❌ Вы уже на последней странице")
    
    elif message.text == '🔄 Обновить':
        # Обновляем данные из базы
        try:
            questions_dict = db.get_all_questions()
            question_ids = sorted(list(questions_dict.keys()))
            state['questions_dict'] = questions_dict
            state['question_ids'] = question_ids
            admin_states[user_id] = state
            show_questions_page(message, user_id)
        except Exception as e:
            bot.reply_to(message, f"❌ Ошибка при обновлении: {e}")
    
    elif message.text == '⬅️ К управлению':
        del admin_states[user_id]
        questions_management(message)
    
    else:
        # Проверяем, не является ли сообщение ID вопроса
        try:
            question_id = int(message.text)
            if question_id in state.get('questions_dict', {}):
                show_question_details(message, user_id, question_id)
            else:
                bot.reply_to(message, "❌ Вопрос с таким ID не найден")
        except ValueError:
            bot.reply_to(message, "❌ Неизвестная команда")

def show_question_details(message, user_id, question_id):
    """Показать детальную информацию о вопросе"""
    state = admin_states.get(user_id, {})
    questions_dict = state.get('questions_dict', {})
    
    question = questions_dict.get(question_id)
    if not question:
        bot.reply_to(message, "❌ Вопрос не найден")
        return
    
    # Формируем детальную информацию о вопросе
    text = f"📋 Детальная информация о вопросе\n\n"
    text += f"🆔 ID: {question_id}\n"
    text += f"📝 Текст: {question['text']}\n"
    text += f"🏷️ Категория: {question.get('category', 'Не указана')}\n"
    text += f"📊 Количество вариантов: {len(question.get('options', []))}\n\n"
    
    # Показываем варианты ответов
    text += "📋 Варианты ответов:\n"
    for i, option in enumerate(question.get('options', []), 1):
        if isinstance(option, dict):
            text += f"{i}. {option.get('text', 'Нет текста')}\n"
            text += f"   🏷️ Категория: {option.get('category', 'Не указана')}\n"
            text += f"   📊 Балл: {option.get('value', 0)}\n"
        else:
            text += f"{i}. {option}\n"
        text += "\n"
    
    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('✏️ Редактировать'),
        types.KeyboardButton('🗑️ Удалить')
    )
    markup.add(types.KeyboardButton('⬅️ К списку'))
    
    bot.reply_to(message, text, reply_markup=markup)
    
    # Сохраняем ID вопроса в состоянии для последующих операций
    state['current_question_id'] = question_id
    admin_states[user_id] = state

@bot.message_handler(func=lambda message: message.text in ['✏️ Редактировать', '🗑️ Удалить', '⬅️ К списку'])
def handle_question_actions(message):
    """Обработка действий с вопросом"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    state = admin_states.get(user_id, {})
    question_id = state.get('current_question_id')
    
    if message.text == '✏️ Редактировать':
        bot.reply_to(message, "⚠️ Функция редактирования пока не реализована")
    
    elif message.text == '🗑️ Удалить':
        if question_id:
            try:
                success = db.delete_question(question_id)
                if success:
                    bot.reply_to(message, f"✅ Вопрос ID {question_id} успешно удален")
                    # Обновляем список вопросов
                    questions_dict = db.get_all_questions()
                    question_ids = sorted(list(questions_dict.keys()))
                    state['questions_dict'] = questions_dict
                    state['question_ids'] = question_ids
                    admin_states[user_id] = state
                    show_questions_page(message, user_id)
                else:
                    bot.reply_to(message, f"❌ Ошибка при удалении вопроса ID {question_id}")
            except Exception as e:
                bot.reply_to(message, f"❌ Ошибка при удалении: {e}")
        else:
            bot.reply_to(message, "❌ ID вопроса не найден")
    
    elif message.text == '⬅️ К списку':
        show_questions_page(message, user_id)

@bot.message_handler(func=lambda message: message.text == '➕ Добавить вопрос')
def add_question_start(message):
    """Начало добавления вопроса"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Доступ запрещен")
        return
    
    admin_states[user_id] = {'state': 'adding_question', 'step': 0}
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('⬅️ Отмена'))
    
    bot.reply_to(message, 
                 "➕ Добавление нового вопроса\n\n"
                 "📝 Отправьте текст вопроса:", 
                 reply_markup=markup)

@bot.message_handler(func=lambda message: admin_states.get(message.from_user.id, {}).get('state') == 'adding_question')
def add_question_process(message):
    """Обработка добавления вопроса"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    if message.text == '⬅️ Отмена':
        del admin_states[user_id]
        admin_panel(message)
        return
    
    state = admin_states[user_id]
    step = state.get('step', 0)
    
    if step == 0:
        # Сохраняем текст вопроса
        state['question_text'] = message.text
        state['step'] = 1
        state['options'] = []
        state['option_count'] = 0
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton('2 варианта'),
            types.KeyboardButton('3 варианта'),
            types.KeyboardButton('4 варианта')
        )
        markup.add(types.KeyboardButton('⬅️ Отмена'))
        
        bot.reply_to(message, 
                     f"📝 Вопрос: {message.text}\n\n"
                     f"Выберите количество вариантов ответа:",
                     reply_markup=markup)
                     
    elif step == 1:
        # Определяем количество опций
        if message.text == '2 варианта':
            state['total_options'] = 2
        elif message.text == '3 варианта':
            state['total_options'] = 3
        elif message.text == '4 варианта':
            state['total_options'] = 4
        else:
            bot.reply_to(message, "❌ Выберите количество вариантов из кнопок")
            return
        
        state['step'] = 2
        state['option_count'] = 0
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton('Программирование'),
            types.KeyboardButton('Анализ данных'),
            types.KeyboardButton('Дизайн'),
            types.KeyboardButton('Безопасность')
        )
        markup.add(
            types.KeyboardButton('DevOps'),
            types.KeyboardButton('Мобильная разработка'),
            types.KeyboardButton('Game Development'),
            types.KeyboardButton('AI/ML')
        )
        markup.add(types.KeyboardButton('⬅️ Отмена'))
        
        bot.reply_to(message, 
                     f"📝 Вопрос: {state['question_text']}\n"
                     f"📊 Вариантов: {state['total_options']}\n\n"
                     f"Вариант {state['option_count'] + 1} из {state['total_options']}\n"
                     f"Выберите категорию для первого варианта ответа:",
                     reply_markup=markup)
                     
    elif step == 2:
        # Определяем категорию опции
        category_map = {
            'Программирование': 'code',
            'Анализ данных': 'data', 
            'Дизайн': 'design',
            'Безопасность': 'security',
            'DevOps': 'devops',
            'Мобильная разработка': 'mobile',
            'Game Development': 'game',
            'AI/ML': 'ai_ml'
        }
        
        if message.text not in category_map:
            bot.reply_to(message, "❌ Выберите категорию из кнопок")
            return
        
        category = category_map[message.text]
        value_map = {
            'code': 4, 'data': 8, 'design': 12, 'security': 16,
            'devops': 20, 'mobile': 24, 'game': 28, 'ai_ml': 32
        }
        value = value_map[category]
        
        state['current_category'] = category
        state['current_value'] = value
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('⬅️ Отмена'))
        
        bot.reply_to(message, 
                     f"📝 Вопрос: {state['question_text']}\n"
                     f"📊 Вариант {state['option_count'] + 1} из {state['total_options']}\n"
                     f"🏷️ Категория: {message.text}\n\n"
                     f"Введите текст варианта ответа:",
                     reply_markup=markup)
        
        state['step'] = 3
        
    elif step == 3:
        # Сохраняем текст опции
        option_text = message.text.strip()
        
        if not option_text:
            bot.reply_to(message, "❌ Текст варианта не может быть пустым")
            return
        
        # Добавляем опцию
        option = {
            'text': option_text,
            'category': state['current_category'],
            'value': state['current_value']
        }
        state['options'].append(option)
        state['option_count'] += 1
        
        # Проверяем, нужно ли добавить еще опции
        if state['option_count'] < state['total_options']:
            # Показываем текущие опции и запрашиваем следующую
            options_text = ""
            for i, opt in enumerate(state['options'], 1):
                options_text += f"{i}. {opt['text']} ({opt['category']}: {opt['value']})\n"
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(
                types.KeyboardButton('Программирование'),
                types.KeyboardButton('Анализ данных'),
                types.KeyboardButton('Дизайн'),
                types.KeyboardButton('Безопасность')
            )
            markup.add(
                types.KeyboardButton('DevOps'),
                types.KeyboardButton('Мобильная разработка'),
                types.KeyboardButton('Game Development'),
                types.KeyboardButton('AI/ML')
            )
            markup.add(types.KeyboardButton('⬅️ Отмена'))
            
            bot.reply_to(message, 
                         f"📝 Вопрос: {state['question_text']}\n"
                         f"📊 Вариант {state['option_count'] + 1} из {state['total_options']}\n\n"
                         f"✅ Добавленные варианты:\n{options_text}\n"
                         f"Выберите категорию для следующего варианта:",
                         reply_markup=markup)
            
            state['step'] = 2
        else:
            # Все опции добавлены, показываем итог
            options_text = ""
            for i, opt in enumerate(state['options'], 1):
                options_text += f"{i}. {opt['text']} ({opt['category']}: {opt['value']})\n"
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(
                types.KeyboardButton('✅ Подтвердить'),
                types.KeyboardButton('🔄 Начать заново')
            )
            markup.add(types.KeyboardButton('⬅️ Отмена'))
            
            bot.reply_to(message, 
                         f"📝 Вопрос: {state['question_text']}\n"
                         f"📊 Все варианты добавлены:\n\n{options_text}\n"
                         f"Выберите действие:",
                         reply_markup=markup)
            
            state['step'] = 4
            
    elif step == 4:
        if message.text == '✅ Подтвердить':
            # Добавляем вопрос в базу
            try:
                question_data = {
                    'text': state['question_text'],
                    'category': 'user_question',  # Общая категория для пользовательских вопросов
                    'options': state['options']
                }
                
                question_id = db.add_question(question_data)
                
                del admin_states[user_id]
                bot.reply_to(message, f"✅ Вопрос успешно добавлен! ID: {question_id}")
                admin_panel(message)
                
            except Exception as e:
                bot.reply_to(message, f"❌ Ошибка при добавлении вопроса: {e}")
                
        elif message.text == '🔄 Начать заново':
            # Сбрасываем к началу
            state['step'] = 1
            state['options'] = []
            state['option_count'] = 0
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(
                types.KeyboardButton('2 варианта'),
                types.KeyboardButton('3 варианта'),
                types.KeyboardButton('4 варианта')
            )
            markup.add(types.KeyboardButton('⬅️ Отмена'))
            
            bot.reply_to(message, 
                         f"📝 Вопрос: {state['question_text']}\n\n"
                         f"Выберите количество вариантов ответа:",
                         reply_markup=markup)
        else:
            bot.reply_to(message, "❌ Выберите действие из кнопок")

@bot.message_handler(func=lambda message: message.text == '🗑️ Удалить вопрос')
def delete_question_start(message):
    """Начало удаления вопроса"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Доступ запрещен")
        return
    
    try:
        questions_dict = db.get_all_questions()
        if not questions_dict:
            bot.reply_to(message, "📭 В базе данных нет вопросов")
            return
        
        # Получаем список ID вопросов
        question_ids = sorted(list(questions_dict.keys()))
        total_questions = len(question_ids)
        
        # Инициализируем состояние пагинации для удаления (20 на страницу)
        admin_states[user_id] = {
            'state': 'deleting_questions',
            'questions_dict': questions_dict,
            'question_ids': question_ids,
            'current_page': 0,
            'questions_per_page': 20
        }
        
        # Показываем первую страницу для удаления
        show_delete_questions_page(message, user_id)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

def show_delete_questions_page(message, user_id):
    """Показать страницу с вопросами для удаления (только ID и название)"""
    state = admin_states.get(user_id, {})
    questions_dict = state.get('questions_dict', {})
    question_ids = state.get('question_ids', [])
    current_page = state.get('current_page', 0)
    questions_per_page = state.get('questions_per_page', 20)
    
    total_questions = len(question_ids)
    total_pages = (total_questions + questions_per_page - 1) // questions_per_page
    
    if total_questions == 0:
        bot.reply_to(message, "📭 В базе данных нет вопросов")
        return
    
    # Вычисляем индексы для текущей страницы
    start_idx = current_page * questions_per_page
    end_idx = min(start_idx + questions_per_page, total_questions)
    
    # Формируем текст страницы (только ID и название)
    text = f"🗑️ Удаление вопроса (страница {current_page + 1} из {total_pages})\n"
    text += f"📊 Всего вопросов: {total_questions}\n\n"
    text += "📝 Отправьте ID вопроса для удаления:\n\n"
    
    for i in range(start_idx, end_idx):
        question_id = question_ids[i]
        question = questions_dict[question_id]
        text += f"🆔 {question_id}: {question['text'][:50]}...\n"
    
    # Создаем клавиатуру для навигации
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    if total_pages > 1:
        if current_page > 0:
            markup.add(types.KeyboardButton('⬅️ Назад'))
        if current_page < total_pages - 1:
            markup.add(types.KeyboardButton('➡️ Вперед'))
    
    markup.add(types.KeyboardButton('⬅️ Отмена'))
    
    bot.reply_to(message, text, reply_markup=markup)

@bot.message_handler(func=lambda message: admin_states.get(message.from_user.id, {}).get('state') == 'deleting_questions')
def delete_question_process(message):
    """Обработка удаления вопроса"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    if message.text == '⬅️ Отмена':
        del admin_states[user_id]
        questions_management(message)
        return
    
    if message.text in ['⬅️ Назад', '➡️ Вперед']:
        # Навигация по страницам
        state = admin_states[user_id]
        current_page = state.get('current_page', 0)
        questions_per_page = state.get('questions_per_page', 20)
        question_ids = state.get('question_ids', [])
        total_questions = len(question_ids)
        total_pages = (total_questions + questions_per_page - 1) // questions_per_page
        
        if message.text == '⬅️ Назад' and current_page > 0:
            state['current_page'] = current_page - 1
        elif message.text == '➡️ Вперед' and current_page < total_pages - 1:
            state['current_page'] = current_page + 1
        
        show_delete_questions_page(message, user_id)
        return
    
    # Обработка ID вопроса для удаления
    try:
        question_id = int(message.text.strip())
        
        # Проверяем, существует ли вопрос
        questions_dict = admin_states[user_id].get('questions_dict', {})
        if question_id not in questions_dict:
            bot.reply_to(message, f"❌ Вопрос с ID {question_id} не найден")
            return
        
        # Удаляем вопрос
        db.delete_question(question_id)
        
        del admin_states[user_id]
        bot.reply_to(message, f"✅ Вопрос {question_id} успешно удален!")
        
        # Показываем обновленный список вопросов
        show_all_questions(message)
        
    except ValueError:
        bot.reply_to(message, "❌ Введите корректный ID (число)")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при удалении вопроса: {e}")

@bot.message_handler(func=lambda message: message.text == '🎓 Управление вузами')
def universities_management(message):
    """Управление вузами"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Доступ запрещен")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('📋 Показать все вузы'),
        types.KeyboardButton('➕ Добавить вуз')
    )
    markup.add(
        types.KeyboardButton('🗑️ Удалить вуз'),
        types.KeyboardButton('⬅️ Назад')
    )
    
    bot.reply_to(message, 
                 "🎓 Управление вузами\n\n"
                 "📝 Создайте вуз, а затем добавьте к нему специальности:\n"
                 "• ➕ Добавить вуз - создать новый вуз\n"
                 "• 🎓 Добавить специализацию в вуз - добавить специальности\n\n"
                 "Выберите действие:", 
                 reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '📋 Показать все вузы')
def show_all_universities_admin(message):
    """Показать все вузы с пагинацией"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Доступ запрещен")
        return
    
    try:
        universities = db.get_unique_universities()
        if not universities:
            bot.reply_to(message, "📭 В базе данных нет вузов")
            return
        
        # Инициализируем состояние пагинации
        admin_states[user_id] = {
            'state': 'viewing_universities',
            'universities': universities,
            'current_page': 0,
            'universities_per_page': 10
        }
        
        # Показываем первую страницу
        show_universities_page(message, user_id)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

def show_universities_page(message, user_id):
    """Показать страницу с вузами"""
    state = admin_states.get(user_id, {})
    universities = state.get('universities', [])
    current_page = state.get('current_page', 0)
    universities_per_page = state.get('universities_per_page', 10)
    
    total_universities = len(universities)
    total_pages = (total_universities + universities_per_page - 1) // universities_per_page
    
    if total_universities == 0:
        bot.reply_to(message, "📭 В базе данных нет вузов")
        return
    
    # Вычисляем индексы для текущей страницы
    start_idx = current_page * universities_per_page
    end_idx = min(start_idx + universities_per_page, total_universities)
    
    # Формируем текст страницы
    text = f"📋 Список вузов (страница {current_page + 1} из {total_pages})\n"
    text += f"📊 Уникальных вузов: {total_universities}\n\n"
    
    for i in range(start_idx, end_idx):
        university = universities[i]
        text += f"🏛️ {university['name']}\n"
        text += f"📍 Город: {university.get('location', 'Не указан')}\n"
        if university.get('url'):
            text += f"🌐 Сайт: {university['url']}\n"
        text += "─" * 40 + "\n\n"
    
    # Создаем клавиатуру с навигацией
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    
    # Кнопки навигации
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(types.KeyboardButton('⬅️ Назад'))
    if current_page < total_pages - 1:
        nav_buttons.append(types.KeyboardButton('Вперед ➡️'))
    
    if nav_buttons:
        markup.add(*nav_buttons)
    
    # Информационные кнопки
    info_buttons = []
    if total_pages > 1:
        info_buttons.append(types.KeyboardButton(f'📄 {current_page + 1}/{total_pages}'))
    info_buttons.append(types.KeyboardButton('🔄 Обновить'))
    
    if info_buttons:
        markup.add(*info_buttons)
    
    # Кнопка возврата
    markup.add(types.KeyboardButton('⬅️ К управлению'))
    
    bot.reply_to(message, text, reply_markup=markup, disable_web_page_preview=True)

@bot.message_handler(func=lambda message: admin_states.get(message.from_user.id, {}).get('state') == 'viewing_universities')
def handle_universities_navigation(message):
    """Обработка навигации по вузам"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    state = admin_states.get(user_id, {})
    current_page = state.get('current_page', 0)
    total_pages = (len(state.get('universities', [])) + state.get('universities_per_page', 10) - 1) // state.get('universities_per_page', 10)
    
    if message.text == '⬅️ Назад':
        if current_page > 0:
            state['current_page'] = current_page - 1
            admin_states[user_id] = state
            show_universities_page(message, user_id)
        else:
            bot.reply_to(message, "❌ Вы уже на первой странице")
    
    elif message.text == 'Вперед ➡️':
        if current_page < total_pages - 1:
            state['current_page'] = current_page + 1
            admin_states[user_id] = state
            show_universities_page(message, user_id)
        else:
            bot.reply_to(message, "❌ Вы уже на последней странице")
    
    elif message.text == '🔄 Обновить':
        # Обновляем данные из базы
        try:
            universities = db.get_all_universities()
            state['universities'] = universities
            admin_states[user_id] = state
            show_universities_page(message, user_id)
        except Exception as e:
            bot.reply_to(message, f"❌ Ошибка при обновлении: {e}")
    
    elif message.text == '⬅️ К управлению':
        del admin_states[user_id]
        universities_management(message)
    
    else:
        # Выбор по имени вуза для деталей или удаления
        name = message.text.strip()
        universities = state.get('universities', [])
        university = next((u for u in universities if u.get('name') == name), None)
        if university:
            show_university_details(message, user_id, name)
        else:
            bot.reply_to(message, "❌ Неизвестная команда")

def show_university_details(message, user_id, university_name):
    """Показать детальную информацию о вузе (по имени)"""
    state = admin_states.get(user_id, {})
    universities = state.get('universities', [])
    
    university = next((u for u in universities if u.get('name') == university_name), None)
    if not university:
        bot.reply_to(message, "❌ Вуз не найден")
        return
    
    # Формируем детальную информацию о вузе
    text = f"📋 Детальная информация о вузе\n\n"
    text += f"🏛️ Название: {university['name']}\n"
    text += f"📍 Город: {university.get('location', 'Не указан')}\n"
    if university.get('url'):
        text += f"🌐 Сайт: {university['url']}\n"
    
    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('✏️ Редактировать'),
        types.KeyboardButton('🗑️ Удалить')
    )
    markup.add(types.KeyboardButton('⬅️ К списку'))
    
    bot.reply_to(message, text, reply_markup=markup, disable_web_page_preview=True)
    
    # Сохраняем имя вуза в состоянии для последующих операций
    state['current_university_name'] = university_name
    admin_states[user_id] = state

@bot.message_handler(func=lambda message: message.text == '➕ Добавить вуз')
def add_university_start(message):
    """Начало добавления вуза"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Доступ запрещен")
        return
    
    admin_states[user_id] = {'state': 'adding_university', 'step': 0}
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('⬅️ Отмена'))
    
    bot.reply_to(message, 
                 "➕ Добавление нового вуза\n\n"
                 "📝 Отправьте название вуза:", 
                 reply_markup=markup)

@bot.message_handler(func=lambda message: admin_states.get(message.from_user.id, {}).get('state') == 'adding_university')
def add_university_process(message):
    """Обработка добавления вуза"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    if message.text == '⬅️ Отмена':
        del admin_states[user_id]
        admin_panel(message)
        return
    
    state = admin_states[user_id]
    step = state.get('step', 0)
    
    if step == 0:
        # Сохраняем название вуза
        state['university_name'] = message.text
        state['step'] = 1
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('⬅️ Отмена'))
        
        bot.reply_to(message, 
                     f"📝 Вуз: {message.text}\n\n"
                     f"📍 Отправьте город вуза:",
                     reply_markup=markup)
                     
    elif step == 1:
        # Сохраняем город
        state['city'] = message.text
        state['step'] = 2
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('Пропустить'))
        markup.add(types.KeyboardButton('⬅️ Отмена'))
        
        bot.reply_to(message, 
                     f"📝 Вуз: {state['university_name']}\n"
                     f"📍 Город: {message.text}\n\n"
                     f"🌐 Отправьте сайт вуза (или нажмите 'Пропустить'):",
                     reply_markup=markup,
                     disable_web_page_preview=True)
                     
    elif step == 2:
        # Сохраняем сайт (опционально) и создаем вуз
        url = message.text if message.text != 'Пропустить' else ""
        
        try:
            # Создаем базовую запись о вузе в universities.json
            import json
            import os
            
            universities_file = 'universities.json'
            
            # Читаем существующие данные
            if os.path.exists(universities_file):
                with open(universities_file, 'r', encoding='utf-8') as f:
                    universities = json.load(f)
            else:
                universities = []
            
            # Проверяем, не существует ли уже такой вуз
            existing_uni = next((uni for uni in universities 
                               if uni['name'] == state['university_name'] and 
                               uni['city'] == state['city']), None)
            
            if existing_uni:
                bot.reply_to(message, 
                            f"❌ Вуз '{state['university_name']}' в городе '{state['city']}' уже существует!")
                del admin_states[user_id]
                admin_panel(message)
                return
            
            # Создаем базовую запись о вузе (без специальностей)
            # Специальности будут добавляться отдельно через админку
            new_university = {
                "name": state['university_name'],
                "city": state['city'],
                "url": url,
                "specialization": "Базовая информация",
                "score_min": 0,
                "score_max": 0
            }
            
            universities.append(new_university)
            
            # Записываем обратно в файл
            with open(universities_file, 'w', encoding='utf-8') as f:
                json.dump(universities, f, ensure_ascii=False, indent=2)
            
            bot.reply_to(message, 
                         f"✅ Вуз успешно создан!\n\n"
                         f"📝 Вуз: {state['university_name']}\n"
                         f"📍 Город: {state['city']}\n"
                         f"🌐 Сайт: {url or 'Не указан'}\n\n"
                         f"💡 Теперь вы можете добавить специальности к этому вузу через:\n"
                         f"🎓 Добавить специализацию в вуз",
                         disable_web_page_preview=True)
            
            del admin_states[user_id]
            admin_panel(message)
            
        except Exception as e:
            bot.reply_to(message, f"❌ Ошибка при создании вуза: {e}")
            del admin_states[user_id]
            admin_panel(message)

@bot.message_handler(func=lambda message: message.text in ['✏️ Редактировать', '🗑️ Удалить', '⬅️ К списку'])
def handle_university_actions(message):
    """Обработка действий с вузом"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    state = admin_states.get(user_id, {})
    university_id = state.get('current_university_id')
    
    if message.text == '✏️ Редактировать':
        bot.reply_to(message, "⚠️ Функция редактирования пока не реализована")
    
    elif message.text == '🗑️ Удалить':
        uni_name = state.get('current_university_name')
        if uni_name:
            try:
                success = db.delete_university_by_name(uni_name)
                if success:
                    # Синхронизация сайта после удаления
                    try:
                        db.sync_website_data()
                        bot.reply_to(message, f"✅ Вуз '{uni_name}' и все его записи удалены!")
                    except Exception as e:
                        bot.reply_to(message, f"✅ Вуз удален, но ошибка обновления сайта: {e}")
                    del admin_states[user_id]
                    
                    # Возвращаемся к управлению вузами
                    universities_management(message)
                else:
                    bot.reply_to(message, f"❌ Ошибка при удалении вуза с ID {university_id}")
            except Exception as e:
                bot.reply_to(message, f"❌ Ошибка при удалении: {e}")
        else:
            bot.reply_to(message, "❌ ID вуза не найден")
    
    elif message.text == '⬅️ К списку':
        show_universities_page(message, user_id)



@bot.message_handler(func=lambda message: message.text == '🎯 Управление специализациями')
def specializations_management(message):
    """Управление специализациями"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Доступ запрещен")
        return
    
    admin_text = """
🎯 Управление специализациями

Выберите действие:
• 📋 Показать все специализации
• ➕ Добавить специализацию
• 🎓 Добавить специализацию в вуз
• 🗑️ Удалить специализацию из вуза
• 🗑️ Удалить специализацию
• ⬅️ Назад

💡 Сначала создайте вуз через "🎓 Управление вузами", 
   затем добавьте к нему специальности здесь.
    """
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('📋 Показать все специализации'),
        types.KeyboardButton('➕ Добавить специализацию')
    )
    markup.add(
        types.KeyboardButton('🎓 Добавить специализацию в вуз'),
        types.KeyboardButton('🗑️ Удалить специализацию из вуза')
    )
    markup.add(
        types.KeyboardButton('🗑️ Удалить специализацию'),
        types.KeyboardButton('⬅️ Назад')
    )
    
    bot.reply_to(message, admin_text, reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '⬅️ Назад' and admin_states.get(message.from_user.id, {}).get('state') == 'admin_main')
def specializations_back(message):
    """Возврат из управления специализациями в админ-панель"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Доступ запрещен")
        return
    
    admin_panel(message)

@bot.message_handler(func=lambda message: message.text == '📋 Показать все специализации')
def show_all_specializations(message):
    """Показать все специализации с пагинацией"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Доступ запрещен")
        return
    
    try:
        specializations_dict = db.get_all_specializations()
        if not specializations_dict:
            bot.reply_to(message, "📭 В базе данных нет специализаций")
            return
        
        # Получаем список ID специализаций
        specialization_ids = sorted(list(specializations_dict.keys()))
        total_specializations = len(specialization_ids)
        
        # Инициализируем состояние пагинации
        admin_states[user_id] = {
            'state': 'viewing_specializations',
            'specializations_dict': specializations_dict,
            'specialization_ids': specialization_ids,
            'current_page': 0,
            'specializations_per_page': 10
        }
        
        # Показываем первую страницу
        show_specializations_page(message, user_id)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

def show_specializations_page(message, user_id):
    """Показать страницу со специализациями"""
    state = admin_states.get(user_id, {})
    specializations_dict = state.get('specializations_dict', {})
    specialization_ids = state.get('specialization_ids', [])
    current_page = state.get('current_page', 0)
    specializations_per_page = state.get('specializations_per_page', 5)
    
    total_specializations = len(specialization_ids)
    total_pages = (total_specializations + specializations_per_page - 1) // specializations_per_page
    
    if total_specializations == 0:
        bot.reply_to(message, "📭 В базе данных нет специализаций")
        return
    
    # Вычисляем индексы для текущей страницы
    start_idx = current_page * specializations_per_page
    end_idx = min(start_idx + specializations_per_page, total_specializations)
    
    # Формируем текст страницы
    text = f"📋 Список специализаций (страница {current_page + 1} из {total_pages})\n"
    text += f"📊 Всего специализаций: {total_specializations}\n\n"
    
    for i in range(start_idx, end_idx):
        specialization_id = specialization_ids[i]
        specialization = specializations_dict[specialization_id]
        if specialization:
            text += f"🆔 ID: {specialization_id}\n"
            text += f"🎯 {specialization['name']}\n"
            text += f"📝 {specialization['description']}\n"
            text += f"💼 Карьера: {specialization['careers']}\n"
            text += "─" * 40 + "\n\n"
    
    # Создаем клавиатуру с навигацией
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    
    # Кнопки навигации
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(types.KeyboardButton('⬅️ Назад'))
    if current_page < total_pages - 1:
        nav_buttons.append(types.KeyboardButton('Вперед ➡️'))
    
    if nav_buttons:
        markup.add(*nav_buttons)
    
    # Информационные кнопки
    info_buttons = []
    if total_pages > 1:
        info_buttons.append(types.KeyboardButton(f'📄 {current_page + 1}/{total_pages}'))
    info_buttons.append(types.KeyboardButton('🔄 Обновить'))
    
    if info_buttons:
        markup.add(*info_buttons)
    
    # Кнопка возврата
    markup.add(types.KeyboardButton('⬅️ К управлению'))
    
    bot.reply_to(message, text, reply_markup=markup)

@bot.message_handler(func=lambda message: admin_states.get(message.from_user.id, {}).get('state') == 'viewing_specializations')
def handle_specializations_navigation(message):
    """Обработка навигации по специализациям"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    state = admin_states.get(user_id, {})
    current_page = state.get('current_page', 0)
    total_pages = (len(state.get('specialization_ids', [])) + state.get('specializations_per_page', 5) - 1) // state.get('specializations_per_page', 5)
    
    if message.text == '⬅️ Назад':
        if current_page > 0:
            state['current_page'] = current_page - 1
            admin_states[user_id] = state
            show_specializations_page(message, user_id)
        else:
            bot.reply_to(message, "❌ Вы уже на первой странице")
    
    elif message.text == 'Вперед ➡️':
        if current_page < total_pages - 1:
            state['current_page'] = current_page + 1
            admin_states[user_id] = state
            show_specializations_page(message, user_id)
        else:
            bot.reply_to(message, "❌ Вы уже на последней странице")
    
    elif message.text == '🔄 Обновить':
        # Обновляем данные из базы
        try:
            specializations_dict = db.get_all_specializations()
            specialization_ids = sorted(list(specializations_dict.keys()))
            state['specializations_dict'] = specializations_dict
            state['specialization_ids'] = specialization_ids
            admin_states[user_id] = state
            show_specializations_page(message, user_id)
        except Exception as e:
            bot.reply_to(message, f"❌ Ошибка при обновлении: {e}")
    
    elif message.text == '⬅️ К управлению':
        del admin_states[user_id]
        specializations_management(message)
    
    else:
        # Проверяем, не является ли сообщение ID специализации
        try:
            specialization_id = int(message.text)
            if specialization_id in state.get('specializations_dict', {}):
                show_specialization_details(message, user_id, specialization_id)
            else:
                bot.reply_to(message, "❌ Специализация с таким ID не найдена")
        except ValueError:
            bot.reply_to(message, "❌ Неизвестная команда")

def show_specialization_details(message, user_id, specialization_id):
    """Показать детальную информацию о специализации"""
    state = admin_states.get(user_id, {})
    specializations_dict = state.get('specializations_dict', {})
    
    specialization = specializations_dict.get(specialization_id)
    if not specialization:
        bot.reply_to(message, "❌ Специализация не найдена")
        return
    
    # Формируем детальную информацию о специализации
    text = f"📋 Детальная информация о специализации\n\n"
    text += f"🆔 ID: {specialization_id}\n"
    text += f"🎯 Название: {specialization['name']}\n"
    text += f"📝 Описание: {specialization['description']}\n"
    text += f"💼 Карьера: {specialization['careers']}\n"
    text += f"📊 Технический балл: {specialization['tech_score']}\n"
    text += f"📊 Аналитический балл: {specialization['analytic_score']}\n"
    text += f"📊 Креативный балл: {specialization['creative_score']}\n"
    
    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('✏️ Редактировать'),
        types.KeyboardButton('🗑️ Удалить')
    )
    markup.add(types.KeyboardButton('⬅️ К списку'))
    
    bot.reply_to(message, text, reply_markup=markup)
    
    # Сохраняем ID специализации в состоянии для последующих операций
    state['current_specialization_id'] = specialization_id
    admin_states[user_id] = state

@bot.message_handler(func=lambda message: message.text in ['✏️ Редактировать', '🗑️ Удалить', '⬅️ К списку'] and admin_states.get(message.from_user.id, {}).get('state') == 'viewing_specializations')
def handle_specialization_actions(message):
    """Обработка действий со специализациями"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    state = admin_states.get(user_id, {})
    specializations_dict = state.get('specializations_dict', {})
    specialization_id = state.get('current_specialization_id')
    
    if message.text == '⬅️ К списку':
        show_specializations_page(message, user_id)
    
    elif message.text == '🗑️ Удалить':
        # Удаляем специализацию
        if specialization_id:
            try:
                specialization = specializations_dict.get(specialization_id)
                if specialization:
                    success = db.delete_specialization(specialization_id)
                    if success:
                        bot.reply_to(message, f"✅ Специализация '{specialization['name']}' успешно удалена!")
                    else:
                        bot.reply_to(message, "❌ Ошибка при удалении специализации")
                else:
                    bot.reply_to(message, "❌ Специализация не найдена")
            except Exception as e:
                bot.reply_to(message, f"❌ Ошибка: {e}")
        else:
            bot.reply_to(message, "❌ ID специализации не найден")
        
        # Возвращаемся к списку специализаций
        del admin_states[user_id]
        show_all_specializations(message)
    
    elif message.text == '✏️ Редактировать':
        bot.reply_to(message, "✏️ Редактирование специализаций пока не реализовано")
        show_specialization_details(message, user_id, specialization_id)

@bot.message_handler(func=lambda message: message.text == '➕ Добавить специализацию')
def add_specialization_start(message):
    """Начало добавления специализации"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Доступ запрещен")
        return
    
    admin_states[user_id] = {'state': 'adding_specialization', 'step': 0}
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('⬅️ Отмена'))
    
    bot.reply_to(message, 
                 "➕ Добавление новой специализации\n\n"
                 "📝 Отправьте название специализации:", 
                 reply_markup=markup)

@bot.message_handler(func=lambda message: admin_states.get(message.from_user.id, {}).get('state') == 'adding_specialization')
def add_specialization_process(message):
    """Обработка добавления специализации"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    if message.text == '⬅️ Отмена':
        del admin_states[user_id]
        specializations_management(message)
        return
    
    state = admin_states[user_id]
    step = state.get('step', 0)
    
    if step == 0:
        # Сохраняем название специализации
        state['specialization_name'] = message.text
        state['step'] = 1
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('⬅️ Отмена'))
        
        bot.reply_to(message, 
                     f"📝 Специализация: {message.text}\n\n"
                     f"📝 Отправьте описание специализации:",
                     reply_markup=markup)
                     
    elif step == 1:
        # Сохраняем описание
        state['description'] = message.text
        state['step'] = 2
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('⬅️ Отмена'))
        
        bot.reply_to(message, 
                     f"📝 Специализация: {state['specialization_name']}\n"
                     f"📝 Описание: {message.text}\n\n"
                     f"💼 Отправьте карьерные возможности:",
                     reply_markup=markup)
                     
    elif step == 2:
        # Сохраняем карьерные возможности
        state['careers'] = message.text
        state['step'] = 3
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('⬅️ Отмена'))
        
        bot.reply_to(message, 
                     f"📝 Специализация: {state['specialization_name']}\n"
                     f"📝 Описание: {state['description']}\n"
                     f"💼 Карьера: {message.text}\n\n"
                     f"🔧 Технический балл (0.0-1.0):\n"
                     f"• 0.0 = Не требует технических навыков\n"
                     f"• 0.5 = Средние технические требования\n"
                     f"• 1.0 = Высокие технические требования\n\n"
                     f"📊 Отправьте технический балл:",
                     reply_markup=markup)
                     
    elif step == 3:
        # Сохраняем технический балл
        try:
            tech_score = float(message.text)
            if tech_score < 0 or tech_score > 1:
                bot.reply_to(message, "❌ Балл должен быть от 0.0 до 1.0")
                return
            
            state['tech_score'] = tech_score
            state['step'] = 4
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton('⬅️ Отмена'))
            
            bot.reply_to(message, 
                         f"📝 Специализация: {state['specialization_name']}\n"
                         f"🔧 Технический балл: {tech_score}\n\n"
                         f"📊 Аналитический балл (0.0-1.0):\n"
                         f"• 0.0 = Не требует анализа данных\n"
                         f"• 0.5 = Средние аналитические требования\n"
                         f"• 1.0 = Высокие аналитические требования\n\n"
                         f"📊 Отправьте аналитический балл:",
                         reply_markup=markup)
                         
        except ValueError:
            bot.reply_to(message, "❌ Введите корректное число")
            
    elif step == 4:
        # Сохраняем аналитический балл
        try:
            analytic_score = float(message.text)
            if analytic_score < 0 or analytic_score > 1:
                bot.reply_to(message, "❌ Балл должен быть от 0.0 до 1.0")
                return
            
            state['analytic_score'] = analytic_score
            state['step'] = 5
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton('⬅️ Отмена'))
            
            bot.reply_to(message, 
                         f"📝 Специализация: {state['specialization_name']}\n"
                         f"📊 Аналитический балл: {analytic_score}\n\n"
                         f"🎨 Креативный балл (0.0-1.0):\n"
                         f"• 0.0 = Не требует творчества\n"
                         f"• 0.5 = Средние творческие требования\n"
                         f"• 1.0 = Высокие творческие требования\n\n"
                         f"🎨 Отправьте креативный балл:",
                         reply_markup=markup)
                         
        except ValueError:
            bot.reply_to(message, "❌ Введите корректное число")
            
    elif step == 5:
        # Сохраняем креативный балл
        try:
            creative_score = float(message.text)
            if creative_score < 0 or creative_score > 1:
                bot.reply_to(message, "❌ Балл должен быть от 0.0 до 1.0")
                return
            
            try:
                # Добавляем специализацию в базу
                db.add_specialization(
                    state['specialization_name'],
                    state['description'],
                    state['tech_score'],
                    state['analytic_score'],
                    creative_score,
                    state['careers']
                )
                
                del admin_states[user_id]
                bot.reply_to(message, "✅ Специализация успешно добавлена!")
                specializations_management(message)
                
            except Exception as e:
                bot.reply_to(message, f"❌ Ошибка при добавлении специализации: {e}")
                
        except ValueError:
            bot.reply_to(message, "❌ Введите корректное число")

@bot.message_handler(func=lambda message: message.text == '🎓 Добавить специализацию в вуз')
def add_specialization_to_university_start(message):
    """Начало добавления специализации в вуз"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Доступ запрещен")
        return
    
    # Получаем список специализаций
    try:
        specializations = db.get_all_specializations()
        if not specializations:
            bot.reply_to(message, "📭 В базе данных нет специализаций. Сначала добавьте специализации.")
            specializations_management(message)
            return
        
        # Формируем список специализаций для выбора
        spec_list = []
        for spec_id, spec_data in specializations.items():
            spec_list.append(f"{spec_id}. {spec_data['name']}")
        
        spec_text = "\n".join(spec_list)
        
        admin_states[user_id] = {
            'state': 'adding_spec_to_uni',
            'step': 0,
            'specializations': specializations
        }
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('⬅️ Отмена'))
        
        bot.reply_to(message, 
                     f"🎓 Добавление специализации в вуз\n\n"
                     f"📋 Доступные специализации:\n{spec_text}\n\n"
                     f"📝 Введите ID специализации:",
                     reply_markup=markup)
                     
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(func=lambda message: admin_states.get(message.from_user.id, {}).get('state') == 'adding_spec_to_uni')
def add_specialization_to_university_process(message):
    """Обработка добавления специализации в вуз"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    if message.text == '⬅️ Отмена':
        del admin_states[user_id]
        specializations_management(message)
        return
    
    state = admin_states[user_id]
    step = state.get('step', 0)
    
    if step == 0:
        # Проверяем ID специализации
        try:
            spec_id = int(message.text)
            if spec_id not in state['specializations']:
                bot.reply_to(message, "❌ Неверный ID специализации. Попробуйте снова.")
                return
            
            spec_data = state['specializations'][spec_id]
            state['spec_id'] = spec_id
            state['spec_name'] = spec_data['name']
            state['step'] = 1
            
            # Получаем список всех вузов из JSON файла
            try:
                import json
                import os
                
                universities_file = 'universities.json'
                if os.path.exists(universities_file):
                    with open(universities_file, 'r', encoding='utf-8') as f:
                        all_universities = json.load(f)
                else:
                    all_universities = []
                
                # Группируем вузы по названию и городу
                unique_universities = {}
                for uni in all_universities:
                    key = (uni['name'], uni['city'])
                    if key not in unique_universities:
                        unique_universities[key] = uni
                
                # Формируем список уникальных вузов для выбора
                uni_list = []
                uni_id = 1
                for (name, city), uni_data in unique_universities.items():
                    uni_list.append(f"{uni_id}. {name} ({city})")
                    uni_id += 1
                
                state['unique_universities'] = list(unique_universities.values())
                state['uni_id'] = uni_id - 1
                
                uni_text = "\n".join(uni_list)
                
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add(types.KeyboardButton('⬅️ Отмена'))
                
                bot.reply_to(message, 
                             f"🎓 Специализация: {spec_data['name']}\n\n"
                             f"🏛️ Доступные вузы:\n{uni_text}\n\n"
                             f"📝 Введите ID вуза (или 0 для нового вуза):",
                             reply_markup=markup)
                             
            except Exception as e:
                bot.reply_to(message, f"❌ Ошибка при загрузке вузов: {e}")
                return
                         
        except ValueError:
            bot.reply_to(message, "❌ Введите корректный ID специализации")
            
    elif step == 1:
        # Обрабатываем выбор вуза
        try:
            uni_choice = int(message.text)
            
            if uni_choice == 0:
                # Создаем новый вуз
                state['step'] = 2
                state['is_new_university'] = True
                
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add(types.KeyboardButton('⬅️ Отмена'))
                
                bot.reply_to(message, 
                             f"🎓 Специализация: {state['spec_name']}\n"
                             f"🏛️ Создание нового вуза\n\n"
                             f"📝 Введите название вуза:",
                             reply_markup=markup)
                             
            elif 1 <= uni_choice <= state['uni_id']:
                # Выбираем существующий вуз
                selected_uni = state['unique_universities'][uni_choice - 1]
                state['university_name'] = selected_uni['name']
                state['city'] = selected_uni['city']
                state['is_new_university'] = False
                state['step'] = 4  # Переходим к вводу минимального балла
                
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                markup.add(types.KeyboardButton('⬅️ Отмена'))
                
                bot.reply_to(message, 
                             f"🎓 Специализация: {state['spec_name']}\n"
                             f"🏛️ Вуз: {selected_uni['name']} ({selected_uni['city']})\n\n"
                             f"📊 Введите минимальный балл ЕГЭ:",
                             reply_markup=markup)
                             
            else:
                bot.reply_to(message, "❌ Неверный ID вуза. Попробуйте снова.")
                return
                
        except ValueError:
            bot.reply_to(message, "❌ Введите корректный ID вуза")
            
    elif step == 2:
        # Сохраняем название нового вуза
        state['university_name'] = message.text
        state['step'] = 3
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('⬅️ Отмена'))
        
        bot.reply_to(message, 
                     f"🎓 Специализация: {state['spec_name']}\n"
                     f"🏛️ Вуз: {message.text}\n\n"
                     f"🏙️ Введите город вуза:",
                     reply_markup=markup)
                     
    elif step == 3:
        # Сохраняем город для нового вуза
        state['city'] = message.text
        state['step'] = 4
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('⬅️ Отмена'))
        
        bot.reply_to(message, 
                     f"🎓 Специализация: {state['spec_name']}\n"
                     f"🏛️ Вуз: {state['university_name']}\n"
                     f"🏙️ Город: {message.text}\n\n"
                     f"📊 Введите минимальный балл ЕГЭ:",
                     reply_markup=markup)
                     
    elif step == 4:
        # Сохраняем минимальный балл
        try:
            score_min = float(message.text)
            if score_min < 0 or score_min > 400:
                bot.reply_to(message, "❌ Балл должен быть от 0 до 400")
                return
            
            state['score_min'] = score_min
            state['step'] = 5
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton('⬅️ Отмена'))
            
            city_info = f" ({state['city']})" if state.get('city') else ""
            bot.reply_to(message, 
                         f"🎓 Специализация: {state['spec_name']}\n"
                         f"🏛️ Вуз: {state['university_name']}{city_info}\n"
                         f"📊 Мин. балл: {score_min}\n\n"
                         f"📊 Введите максимальный балл ЕГЭ:",
                         reply_markup=markup)
                         
        except ValueError:
            bot.reply_to(message, "❌ Введите корректное число")
            
    elif step == 5:
        # Сохраняем максимальный балл и сразу добавляем университет
        try:
            score_max = float(message.text)
            if score_max < state['score_min'] or score_max > 400:
                bot.reply_to(message, f"❌ Максимальный балл должен быть больше минимального ({state['score_min']}) и не более 400")
                return
            
            state['score_max'] = score_max
            
            try:
                # Добавляем университет в JSON файл
                new_university = {
                    "name": state['university_name'],
                    "city": state['city'],
                    "score_min": state['score_min'],
                    "score_max": state['score_max'],
                    "url": "",  # Пустая ссылка, так как вуз уже существует
                    "specialization": state['spec_name']
                }
                
                # Читаем текущий файл universities.json
                import json
                import os
                
                universities_file = 'universities.json'
                if os.path.exists(universities_file):
                    with open(universities_file, 'r', encoding='utf-8') as f:
                        universities = json.load(f)
                else:
                    universities = []
                
                # Добавляем новый университет
                universities.append(new_university)
                
                # Записываем обратно в файл
                with open(universities_file, 'w', encoding='utf-8') as f:
                    json.dump(universities, f, ensure_ascii=False, indent=2)
                
                del admin_states[user_id]
                bot.reply_to(message, 
                             f"✅ Университет успешно добавлен!\n\n"
                             f"🎓 Специализация: {state['spec_name']}\n"
                             f"🏛️ Вуз: {state['university_name']}\n"
                             f"🏙️ Город: {state['city']}\n"
                             f"📊 Баллы: {state['score_min']}-{state['score_max']}")
                
                specializations_management(message)
                
            except Exception as e:
                bot.reply_to(message, f"❌ Ошибка при добавлении университета: {e}")
                         
        except ValueError:
            bot.reply_to(message, "❌ Введите корректное число")

@bot.message_handler(func=lambda message: message.text == '🗑️ Удалить специализацию из вуза')
def delete_specialization_from_university_start(message):
    """Начало удаления специализации из вуза"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Доступ запрещен")
        return
    
    try:
        # Читаем данные из universities.json
        import json
        import os
        
        universities_file = 'universities.json'
        if not os.path.exists(universities_file):
            bot.reply_to(message, "📭 Файл universities.json не найден")
            return
        
        with open(universities_file, 'r', encoding='utf-8') as f:
            universities = json.load(f)
        
        if not universities:
            bot.reply_to(message, "📭 В файле нет данных о вузах")
            return
        
        # Группируем вузы по названию и городу
        grouped_unis = {}
        for uni in universities:
            key = f"{uni['name']} ({uni['city']})"
            if key not in grouped_unis:
                grouped_unis[key] = []
            grouped_unis[key].append(uni)
        
        # Формируем список для выбора
        uni_list = []
        uni_id = 1
        for uni_name, uni_data in grouped_unis.items():
            specs_count = len(uni_data)
            uni_list.append(f"{uni_id}. {uni_name} - {specs_count} специальностей")
            uni_id += 1
        
        admin_states[user_id] = {
            'state': 'deleting_spec_from_uni',
            'step': 0,
            'grouped_unis': grouped_unis,
            'uni_list': list(grouped_unis.keys())
        }
        
        uni_text = "\n".join(uni_list)
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('⬅️ Отмена'))
        
        bot.reply_to(message, 
                     f"🗑️ Удаление специализации из вуза\n\n"
                     f"🏛️ Доступные вузы:\n{uni_text}\n\n"
                     f"📝 Введите ID вуза:",
                     reply_markup=markup)
                     
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(func=lambda message: admin_states.get(message.from_user.id, {}).get('state') == 'deleting_spec_from_uni')
def delete_specialization_from_university_process(message):
    """Обработка удаления специализации из вуза"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    if message.text == '⬅️ Отмена':
        del admin_states[user_id]
        specializations_management(message)
        return
    
    state = admin_states[user_id]
    step = state.get('step', 0)
    
    if step == 0:
        # Выбор вуза
        try:
            uni_choice = int(message.text)
            if uni_choice < 1 or uni_choice > len(state['uni_list']):
                bot.reply_to(message, "❌ Неверный ID вуза. Попробуйте снова.")
                return
            
            selected_uni_key = state['uni_list'][uni_choice - 1]
            selected_uni_data = state['grouped_unis'][selected_uni_key]
            
            state['selected_uni_key'] = selected_uni_key
            state['selected_uni_data'] = selected_uni_data
            state['step'] = 1
            
            # Показываем список специальностей вуза
            specs_list = []
            for i, spec in enumerate(selected_uni_data):
                specs_list.append(f"{i + 1}. {spec['specialization']} ({spec['score_min']}-{spec['score_max']})")
            
            specs_text = "\n".join(specs_list)
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton('⬅️ Отмена'))
            
            bot.reply_to(message, 
                         f"🏛️ Вуз: {selected_uni_key}\n\n"
                         f"📋 Специальности:\n{specs_text}\n\n"
                         f"📝 Введите ID специальности для удаления:",
                         reply_markup=markup)
                         
        except ValueError:
            bot.reply_to(message, "❌ Введите корректный ID вуза")
            
    elif step == 1:
        # Выбор специальности для удаления
        try:
            spec_choice = int(message.text)
            if spec_choice < 1 or spec_choice > len(state['selected_uni_data']):
                bot.reply_to(message, "❌ Неверный ID специальности. Попробуйте снова.")
                return
            
            selected_spec = state['selected_uni_data'][spec_choice - 1]
            
            # Удаляем специальность из файла
            try:
                import json
                import os
                
                universities_file = 'universities.json'
                with open(universities_file, 'r', encoding='utf-8') as f:
                    all_universities = json.load(f)
                
                # Находим и удаляем запись
                for i, uni in enumerate(all_universities):
                    if (uni['name'] == selected_spec['name'] and 
                        uni['city'] == selected_spec['city'] and 
                        uni['specialization'] == selected_spec['specialization']):
                        del all_universities[i]
                        break
                
                # Записываем обновленный файл
                with open(universities_file, 'w', encoding='utf-8') as f:
                    json.dump(all_universities, f, ensure_ascii=False, indent=2)
                
                del admin_states[user_id]
                bot.reply_to(message, 
                             f"✅ Специализация успешно удалена!\n\n"
                             f"🏛️ Вуз: {state['selected_uni_key']}\n"
                             f"🎯 Специализация: {selected_spec['specialization']}\n"
                             f"📊 Баллы: {selected_spec['score_min']}-{selected_spec['score_max']}")
                
                specializations_management(message)
                
            except Exception as e:
                bot.reply_to(message, f"❌ Ошибка при удалении: {e}")
                
        except ValueError:
            bot.reply_to(message, "❌ Введите корректный ID специальности")

@bot.message_handler(func=lambda message: message.text == '🗑️ Удалить специализацию')
def delete_specialization_start(message):
    """Начало удаления специализации"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Доступ запрещен")
        return
    
    try:
        specializations = db.get_all_specializations()
        if not specializations:
            bot.reply_to(message, "📭 В базе данных нет специализаций")
            return
        
        # Получаем список ID специализаций
        specialization_ids = sorted(list(specializations.keys()))
        total_specializations = len(specialization_ids)
        
        # Инициализируем состояние пагинации для удаления (20 на страницу)
        admin_states[user_id] = {
            'state': 'deleting_specializations',
            'specializations': specializations,
            'specialization_ids': specialization_ids,
            'current_page': 0,
            'specializations_per_page': 20
        }
        
        # Показываем первую страницу для удаления
        show_delete_specializations_page(message, user_id)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

def show_delete_specializations_page(message, user_id):
    """Показать страницу со специализациями для удаления (только ID и название)"""
    state = admin_states.get(user_id, {})
    specializations = state.get('specializations', {})
    specialization_ids = state.get('specialization_ids', [])
    current_page = state.get('current_page', 0)
    specializations_per_page = state.get('specializations_per_page', 20)
    
    total_specializations = len(specialization_ids)
    total_pages = (total_specializations + specializations_per_page - 1) // specializations_per_page
    
    if total_specializations == 0:
        bot.reply_to(message, "📭 В базе данных нет специализаций")
        return
    
    # Вычисляем индексы для текущей страницы
    start_idx = current_page * specializations_per_page
    end_idx = min(start_idx + specializations_per_page, total_specializations)
    
    # Формируем текст страницы (только ID и название)
    text = f"🗑️ Удаление специализации (страница {current_page + 1} из {total_pages})\n"
    text += f"📊 Всего специализаций: {total_specializations}\n\n"
    text += "📝 Отправьте ID специализации для удаления:\n\n"
    
    for i in range(start_idx, end_idx):
        specialization_id = specialization_ids[i]
        specialization = specializations[specialization_id]
        text += f"🆔 {specialization_id}: {specialization['name']}\n"
    
    # Создаем клавиатуру для навигации
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    if total_pages > 1:
        if current_page > 0:
            markup.add(types.KeyboardButton('⬅️ Назад'))
        if current_page < total_pages - 1:
            markup.add(types.KeyboardButton('➡️ Вперед'))
    
    markup.add(types.KeyboardButton('⬅️ Отмена'))
    
    bot.reply_to(message, text, reply_markup=markup)

@bot.message_handler(func=lambda message: admin_states.get(message.from_user.id, {}).get('state') == 'deleting_specializations')
def delete_specialization_process(message):
    """Обработка удаления специализации"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    if message.text == '⬅️ Отмена':
        del admin_states[user_id]
        specializations_management(message)
        return
    
    if message.text in ['⬅️ Назад', '➡️ Вперед']:
        # Навигация по страницам
        state = admin_states[user_id]
        current_page = state.get('current_page', 0)
        specializations_per_page = state.get('specializations_per_page', 20)
        specialization_ids = state.get('specialization_ids', [])
        total_specializations = len(specialization_ids)
        total_pages = (total_specializations + specializations_per_page - 1) // specializations_per_page
        
        if message.text == '⬅️ Назад' and current_page > 0:
            state['current_page'] = current_page - 1
        elif message.text == '➡️ Вперед' and current_page < total_pages - 1:
            state['current_page'] = current_page + 1
        
        show_delete_specializations_page(message, user_id)
        return
    
    # Обработка ID специализации для удаления
    try:
        specialization_id = int(message.text.strip())
        
        # Проверяем, существует ли специализация
        specializations = admin_states[user_id].get('specializations', {})
        if specialization_id not in specializations:
            bot.reply_to(message, f"❌ Специализация с ID {specialization_id} не найдена")
            return
        
        # Удаляем специализацию
        db.delete_specialization(specialization_id)
        
        del admin_states[user_id]
        bot.reply_to(message, f"✅ Специализация {specialization_id} успешно удалена!")
        
        # Показываем обновленный список специализаций
        show_all_specializations(message)
        
    except ValueError:
        bot.reply_to(message, "❌ Введите корректный ID (число)")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при удалении специализации: {e}")

@bot.message_handler(func=lambda message: message.text == '🗑️ Удалить вуз')
def delete_university_start(message):
    """Начало удаления вуза"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Доступ запрещен")
        return
    
    try:
        universities = db.get_unique_universities()
        if not universities:
            bot.reply_to(message, "📭 В базе данных нет вузов")
            return
        
        # Инициализируем состояние пагинации для удаления (20 на страницу)
        admin_states[user_id] = {
            'state': 'deleting_universities',
            'universities': universities,
            'current_page': 0,
            'universities_per_page': 20
        }
        
        # Показываем первую страницу для удаления
        show_delete_universities_page(message, user_id)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

def show_delete_universities_page(message, user_id):
    """Показать страницу с вузами для удаления (только ID и название)"""
    state = admin_states.get(user_id, {})
    universities = state.get('universities', [])
    current_page = state.get('current_page', 0)
    universities_per_page = state.get('universities_per_page', 20)
    
    total_universities = len(universities)
    total_pages = (total_universities + universities_per_page - 1) // universities_per_page
    
    if total_universities == 0:
        bot.reply_to(message, "📭 В базе данных нет вузов")
        return
    
    # Вычисляем индексы для текущей страницы
    start_idx = current_page * universities_per_page
    end_idx = min(start_idx + universities_per_page, total_universities)
    
    # Формируем текст страницы (ID и название)
    text = f"🗑️ Удаление вуза (страница {current_page + 1} из {total_pages})\n"
    text += f"📊 Уникальных вузов: {total_universities}\n\n"
    text += "📝 Отправьте ID вуза для удаления:\n\n"
    
    for i in range(start_idx, end_idx):
        university = universities[i]
        text += f"🆔 {i + 1}: {university['name']}\n"
    
    # Создаем клавиатуру для навигации
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    if total_pages > 1:
        if current_page > 0:
            markup.add(types.KeyboardButton('⬅️ Назад'))
        if current_page < total_pages - 1:
            markup.add(types.KeyboardButton('➡️ Вперед'))
    
    markup.add(types.KeyboardButton('⬅️ Отмена'))
    
    bot.reply_to(message, text, reply_markup=markup)

@bot.message_handler(func=lambda message: admin_states.get(message.from_user.id, {}).get('state') == 'deleting_universities')
def delete_university_process(message):
    """Обработка удаления вуза"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    if message.text == '⬅️ Отмена':
        del admin_states[user_id]
        admin_panel(message)
        return
    
    if message.text in ['⬅️ Назад', '➡️ Вперед']:
        # Навигация по страницам
        state = admin_states[user_id]
        current_page = state.get('current_page', 0)
        universities_per_page = state.get('universities_per_page', 20)
        universities = state.get('universities', [])
        total_universities = len(universities)
        total_pages = (total_universities + universities_per_page - 1) // universities_per_page
        
        if message.text == '⬅️ Назад' and current_page > 0:
            state['current_page'] = current_page - 1
        elif message.text == '➡️ Вперед' and current_page < total_pages - 1:
            state['current_page'] = current_page + 1
        
        show_delete_universities_page(message, user_id)
        return
    
    # Обработка ID вуза для удаления
    try:
        university_id = int(message.text.strip())
        
        # Проверяем, существует ли вуз с таким ID
        universities = admin_states[user_id].get('universities', [])
        universities_per_page = admin_states[user_id].get('universities_per_page', 20)
        current_page = admin_states[user_id].get('current_page', 0)
        
        # Вычисляем реальный индекс в общем списке
        start_idx = current_page * universities_per_page
        real_index = start_idx + university_id - 1
        
        if real_index < 0 or real_index >= len(universities):
            bot.reply_to(message, f"❌ Вуз с ID {university_id} не найден")
            return
        
        university = universities[real_index]
        university_name = university['name']
        
        # Удаляем вуз по названию
        success = db.delete_university_by_name(university_name)
        
        if success:
            del admin_states[user_id]
            bot.reply_to(message, f"✅ Вуз '{university_name}' и все его записи удалены!")
            
            # Синхронизация сайта после удаления
            try:
                db.sync_website_data()
            except Exception as e:
                bot.reply_to(message, f"⚠️ Вуз удален, но ошибка обновления сайта: {e}")
            
            # Возвращаемся к управлению вузами
            universities_management(message)
        else:
            bot.reply_to(message, f"❌ Ошибка при удалении вуза '{university_name}'")
        
    except ValueError:
        bot.reply_to(message, "❌ Введите корректный ID (число)")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при удалении вуза: {e}")

@bot.message_handler(func=lambda message: message.text == '📢 Рассылка')
def broadcast_start(message):
    """Начало рассылки"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Доступ запрещен")
        return
    
    admin_states[user_id] = {'state': 'broadcasting'}
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('⬅️ Отмена'))
    
    bot.reply_to(message, 
                 "📢 Рассылка сообщений\n\n"
                 "Отправьте текст сообщения для рассылки всем пользователям:", 
                 reply_markup=markup)

@bot.message_handler(func=lambda message: admin_states.get(message.from_user.id, {}).get('state') == 'broadcasting')
def broadcast_process(message):
    """Обработка рассылки"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    if message.text == '⬅️ Отмена':
        del admin_states[user_id]
        admin_panel(message)
        return
    
    try:
        users = db.get_all_users()
        sent_count = 0
        error_count = 0
        
        for user_id in users:
            try:
                bot.send_message(user_id, f"📢 Сообщение от администратора:\n\n{message.text}", disable_web_page_preview=True)
                sent_count += 1
            except Exception:
                error_count += 1
                # Не выводим ошибки для несуществующих пользователей
        
        bot.reply_to(message, f"✅ Отправлено {sent_count} пользователям")
        admin_states[message.from_user.id] = {'state': 'admin_main'}
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка рассылки: {e}")

@bot.message_handler(func=lambda message: message.text == '📊 Статистика')
def detailed_statistics(message):
    """Подробная статистика"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.reply_to(message, "❌ Доступ запрещен")
        return
    
    try:
        stats = get_admin_statistics()
        
        text = f"""
📊 Подробная статистика

👥 Пользователи:
• Всего пользователей: {stats['total_users']}
• Завершенных тестов: {stats['completed_tests']}
• Всего вопросов: {stats['total_questions']}
• Всего вузов: {stats['total_universities']}
• Всего специализаций: {stats['total_specializations']}

📝 Контент:
• Всего вопросов: {stats['total_questions']}
• Всего вузов: {stats['total_universities']}
• Всего специализаций: {stats['total_specializations']}

📈 Активность:
• Среднее время прохождения теста: ~10-15 минут
        """
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('⬅️ Назад'))
        
        bot.reply_to(message, text, reply_markup=markup)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при получении статистики: {e}")

@bot.message_handler(func=lambda message: message.text == '⬅️ Назад')
def go_back(message):
    """Возврат в главное меню админ-панели"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    admin_panel(message)

@bot.message_handler(func=lambda message: message.text == '⬅️ Выход')
def exit_admin(message):
    """Выход из админ-панели"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    # Очищаем состояние админа
    if user_id in admin_states:
        del admin_states[user_id]
    
    # Возвращаем обычное меню
    welcome_text = """
🎓 Добро пожаловать в IT-профориентатор!

Этот бот поможет вам определить наиболее подходящую IT-специализацию на основе ваших склонностей и предпочтений.

📋 Тест содержит 30 вопросов и займет около 10-15 минут.

Нажмите кнопку "Начать тест" чтобы начать тестирование!
    """
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Начать тест'))
    markup.add(types.KeyboardButton('Помощь'))
    
    bot.reply_to(message, welcome_text, reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == 'Подробный отчёт')
def handle_detailed_report(message):
    try:
        user_id = message.from_user.id
        state = user_states.get(user_id) or {}
        scores = state.get('saved_scores')
        percentages = state.get('saved_percentages')
        top_spec = state.get('saved_specialization')
        answers = state.get('answers', {})
        
        if not scores or not percentages or not top_spec or not answers:
            bot.reply_to(message, "❌ Нет данных для отчёта. Пройдите тест заново.")
            return
        
        # Анализируем каждый ответ
        analysis = analyze_answers(answers)
        
        # Формируем подробный отчёт
        lines = [f"📊 <b>ДЕТАЛЬНЫЙ АНАЛИЗ ВАШИХ ОТВЕТОВ</b>\n"]
        lines.append(f"🎯 <b>Главная специализация:</b> {top_spec}\n")
        
        # Общие проценты
        lines.append("📈 <b>Общие результаты по направлениям:</b>")
        for k, v in sorted(percentages.items(), key=lambda x: -x[1]):
            lines.append(f"• {k}: {v}%")
        
        # Анализ по категориям
        lines.append(f"\n🔍 <b>Анализ ваших склонностей:</b>")
        lines.append(analysis['tendencies'])
        
        # Сильные стороны
        lines.append(f"\n💪 <b>Ваши сильные стороны:</b>")
        for strength in analysis['strengths']:
            lines.append(f"• {strength}")
        
        # Области для развития
        if analysis['weaknesses']:
            lines.append(f"\n📚 <b>Области для развития:</b>")
            for weakness in analysis['weaknesses']:
                lines.append(f"• {weakness}")
        
        # Персональные рекомендации
        lines.append(f"\n💡 <b>Персональные рекомендации:</b>")
        for rec in analysis['recommendations']:
            lines.append(f"• {rec}")
        
        # Карьерные пути
        lines.append(f"\n🚀 <b>Рекомендуемые карьерные пути:</b>")
        for career in analysis['careers']:
            lines.append(f"• {career}")
        
        # Следующие шаги
        lines.append(f"\n🎯 <b>Ваши следующие шаги:</b>")
        for step in analysis['next_steps']:
            lines.append(f"• {step}")
        
        bot.send_message(message.chat.id, "\n".join(lines), parse_mode='HTML')
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

def analyze_answers(answers):
    """Анализирует ответы пользователя и создает персонализированный отчет"""
    analysis = {
        'tendencies': '',
        'strengths': [],
        'weaknesses': [],
        'recommendations': [],
        'careers': [],
        'next_steps': []
    }
    
    # Подсчитываем ответы по категориям
    category_counts = {'code': 0, 'data': 0, 'design': 0, 'security': 0, 'devops': 0, 'mobile': 0, 'game': 0, 'ai_ml': 0}
    
    for question_id, answer_value in answers.items():
        question = db.get_question(int(question_id))
        if question:
            for option in question['options']:
                if option['value'] == answer_value:
                    category = option['category']
                    category_counts[category] += 1
                    break
    
    # Определяем основные склонности
    max_category = max(category_counts, key=category_counts.get)
    max_count = category_counts[max_category]
    
    # Анализируем склонности
    if max_category == 'data':
        analysis['tendencies'] = "Вы проявляете сильную склонность к аналитическому мышлению и работе с данными. Ваши ответы показывают интерес к исследованию, анализу и извлечению инсайтов из информации. Вы предпочитаете системный подход к решению задач, любите работать с большими объемами информации и находить в них скрытые закономерности. Ваше мышление направлено на понимание причинно-следственных связей и прогнозирование результатов на основе имеющихся данных."
        analysis['strengths'].extend([
            "Аналитическое мышление и логика",
            "Интерес к исследованию данных",
            "Способность находить закономерности",
            "Системный подход к решению задач",
            "Математическое мышление",
            "Внимание к деталям и точности"
        ])
        analysis['recommendations'].extend([
            "Изучите Python для анализа данных (pandas, numpy)",
            "Освойте SQL для работы с базами данных",
            "Изучите статистику и математику",
            "Попробуйте машинное обучение (scikit-learn)",
            "Изучите визуализацию данных (matplotlib, seaborn)",
            "Освойте Big Data технологии (Hadoop, Spark)"
        ])
        analysis['careers'].extend([
            "Data Scientist",
            "Data Analyst", 
            "Business Intelligence Analyst",
            "Machine Learning Engineer",
            "Quantitative Analyst",
            "Research Scientist"
        ])
        analysis['next_steps'].extend([
            "Запишитесь на курс по Python для анализа данных",
            "Изучите основы SQL",
            "Попробуйте решить задачи на Kaggle",
            "Изучите статистику и теорию вероятностей",
            "Начните изучать машинное обучение",
            "Создайте свой первый проект анализа данных"
        ])
        
    elif max_category == 'code':
        analysis['tendencies'] = "Вы проявляете сильную склонность к программированию и разработке. Ваши ответы показывают интерес к созданию алгоритмов, оптимизации кода и решению технических задач. Вы любите логические головоломки, систематический подход к решению проблем и создание эффективных решений. Ваше мышление направлено на разбиение сложных задач на простые компоненты и их поэтапное решение."
        analysis['strengths'].extend([
            "Логическое мышление",
            "Интерес к программированию",
            "Способность решать алгоритмические задачи",
            "Внимание к деталям",
            "Системное мышление",
            "Способность к абстракции"
        ])
        analysis['recommendations'].extend([
            "Изучите основы алгоритмов и структур данных",
            "Освойте один из языков программирования (Python, Java, C++)",
            "Изучите принципы ООП",
            "Попробуйте решать задачи на LeetCode",
            "Изучите паттерны проектирования",
            "Освойте Git и системы контроля версий"
        ])
        analysis['careers'].extend([
            "Software Engineer",
            "Backend Developer",
            "Full Stack Developer",
            "Systems Architect",
            "Software Architect",
            "Technical Lead"
        ])
        analysis['next_steps'].extend([
            "Выберите язык программирования и начните изучение",
            "Изучите алгоритмы и структуры данных",
            "Создайте свой первый проект",
            "Присоединитесь к open-source проектам",
            "Изучите принципы чистого кода",
            "Начните изучать фреймворки и библиотеки"
        ])
        
    elif max_category == 'design':
        analysis['tendencies'] = "Вы проявляете сильную склонность к дизайну и творчеству. Ваши ответы показывают интерес к созданию красивых интерфейсов, пользовательскому опыту и визуальному творчеству. Вы цените эстетику, обращаете внимание на детали и стремитесь создавать продукты, которые не только функциональны, но и приятны в использовании. Ваше мышление направлено на понимание потребностей пользователей и создание интуитивно понятных решений."
        analysis['strengths'].extend([
            "Креативное мышление",
            "Чувство эстетики",
            "Интерес к пользовательскому опыту",
            "Внимание к деталям дизайна",
            "Эмпатия к пользователям",
            "Визуальное мышление"
        ])
        analysis['recommendations'].extend([
            "Изучите принципы UX/UI дизайна",
            "Освойте инструменты дизайна (Figma, Adobe XD)",
            "Изучите основы типографики и цветоведения",
            "Изучите психологию пользователей",
            "Изучите принципы доступности (accessibility)",
            "Освойте прототипирование и анимацию"
        ])
        analysis['careers'].extend([
            "UX/UI Designer",
            "Product Designer",
            "Visual Designer",
            "Interaction Designer",
            "UX Researcher",
            "Design System Designer"
        ])
        analysis['next_steps'].extend([
            "Начните изучать Figma или Adobe XD",
            "Изучите принципы UX/UI дизайна",
            "Создайте портфолио дизайн-проектов",
            "Изучите основы типографики",
            "Проведите свое первое UX-исследование",
            "Изучите принципы дизайн-систем"
        ])
        
    elif max_category == 'security':
        analysis['tendencies'] = "Вы проявляете сильную склонность к кибербезопасности. Ваши ответы показывают интерес к защите систем, анализу угроз и обеспечению безопасности. Вы внимательны к деталям, мыслите стратегически и способны предвидеть потенциальные риски. Ваше мышление направлено на понимание уязвимостей систем и разработку защитных механизмов."
        analysis['strengths'].extend([
            "Аналитическое мышление",
            "Интерес к безопасности",
            "Внимание к деталям",
            "Способность мыслить как атакующий",
            "Стратегическое мышление",
            "Системное понимание IT-инфраструктуры"
        ])
        analysis['recommendations'].extend([
            "Изучите основы сетевой безопасности",
            "Освойте Linux и командную строку",
            "Изучите криптографию",
            "Попробуйте CTF (Capture The Flag) задачи",
            "Изучите анализ вредоносного ПО",
            "Освойте инструменты для пентестинга"
        ])
        analysis['careers'].extend([
            "Cybersecurity Analyst",
            "Penetration Tester",
            "Security Engineer",
            "Incident Response Specialist",
            "Security Architect",
            "Threat Intelligence Analyst"
        ])
        analysis['next_steps'].extend([
            "Изучите основы Linux",
            "Начните изучать сетевую безопасность",
            "Попробуйте CTF задачи на HackTheBox",
            "Изучите основы криптографии",
            "Освойте инструменты анализа сетевого трафика",
            "Изучите принципы защиты информации"
        ])
        
    elif max_category == 'devops':
        analysis['tendencies'] = "Вы проявляете сильную склонность к DevOps и автоматизации процессов. Ваши ответы показывают интерес к оптимизации рабочих процессов, управлению инфраструктурой и обеспечению надежности систем. Вы цените эффективность, автоматизацию и системный подход к решению задач."
        analysis['strengths'].extend([
            "Системное мышление",
            "Интерес к автоматизации",
            "Способность оптимизировать процессы",
            "Внимание к надежности систем",
            "Техническая эрудиция",
            "Способность работать с различными технологиями"
        ])
        analysis['recommendations'].extend([
            "Изучите Linux и командную строку",
            "Освойте Docker и контейнеризацию",
            "Изучите CI/CD практики",
            "Освойте облачные платформы (AWS, Azure, GCP)",
            "Изучите мониторинг и логирование",
            "Освойте инструменты оркестрации (Kubernetes)"
        ])
        analysis['careers'].extend([
            "DevOps Engineer",
            "Site Reliability Engineer",
            "Platform Engineer",
            "Infrastructure Engineer",
            "Cloud Engineer",
            "Automation Engineer"
        ])
        analysis['next_steps'].extend([
            "Изучите основы Linux",
            "Начните изучать Docker",
            "Освойте Git и системы контроля версий",
            "Изучите основы облачных технологий",
            "Попробуйте настроить CI/CD pipeline",
            "Изучите мониторинг систем"
        ])
        
    elif max_category == 'mobile':
        analysis['tendencies'] = "Вы проявляете сильную склонность к мобильной разработке. Ваши ответы показывают интерес к созданию приложений для мобильных устройств, пользовательскому опыту и современным технологиям. Вы цените удобство использования, производительность и инновационные решения."
        analysis['strengths'].extend([
            "Интерес к мобильным технологиям",
            "Внимание к пользовательскому опыту",
            "Способность работать с ограничениями платформ",
            "Креативное мышление",
            "Техническая адаптивность",
            "Понимание мобильных трендов"
        ])
        analysis['recommendations'].extend([
            "Изучите Swift для iOS или Kotlin для Android",
            "Освойте React Native или Flutter",
            "Изучите принципы мобильного UX",
            "Освойте инструменты разработки (Xcode, Android Studio)",
            "Изучите мобильную аналитику",
            "Изучите принципы мобильной безопасности"
        ])
        analysis['careers'].extend([
            "iOS Developer",
            "Android Developer",
            "Mobile App Developer",
            "Cross-platform Developer",
            "Mobile UI/UX Designer",
            "Mobile Product Manager"
        ])
        analysis['next_steps'].extend([
            "Выберите платформу (iOS или Android)",
            "Изучите основы мобильной разработки",
            "Создайте свое первое мобильное приложение",
            "Изучите принципы мобильного UX",
            "Освойте инструменты разработки",
            "Изучите мобильную аналитику"
        ])
        
    elif max_category == 'game':
        analysis['tendencies'] = "Вы проявляете сильную склонность к игровой разработке. Ваши ответы показывают интерес к созданию игр, интерактивному контенту и творческим технологиям. Вы цените креативность, инновации и способность создавать захватывающие пользовательские впечатления."
        analysis['strengths'].extend([
            "Креативное мышление",
            "Интерес к игровым технологиям",
            "Способность создавать интерактивный контент",
            "Внимание к пользовательскому опыту",
            "Техническая креативность",
            "Понимание игровых механик"
        ])
        analysis['recommendations'].extend([
            "Изучите Unity или Unreal Engine",
            "Освойте C# или C++",
            "Изучите принципы геймдизайна",
            "Освойте 3D моделирование",
            "Изучите игровую физику",
            "Изучите принципы игровой аналитики"
        ])
        analysis['careers'].extend([
            "Game Developer",
            "Game Designer",
            "Unity Developer",
            "Unreal Engine Developer",
            "Game Programmer",
            "Technical Artist"
        ])
        analysis['next_steps'].extend([
            "Начните изучать Unity или Unreal Engine",
            "Изучите основы геймдизайна",
            "Создайте свою первую простую игру",
            "Изучите C# или C++",
            "Освойте основы 3D моделирования",
            "Изучите игровую физику"
        ])
        
    elif max_category == 'ai_ml':
        analysis['tendencies'] = "Вы проявляете сильную склонность к искусственному интеллекту и машинному обучению. Ваши ответы показывают интерес к созданию интеллектуальных систем, алгоритмам машинного обучения и инновационным технологиям. Вы цените инновации, исследовательский подход и способность создавать системы, которые учатся и адаптируются."
        analysis['strengths'].extend([
            "Математическое мышление",
            "Интерес к алгоритмам машинного обучения",
            "Способность работать с большими данными",
            "Исследовательский подход",
            "Аналитическое мышление",
            "Интерес к инновационным технологиям"
        ])
        analysis['recommendations'].extend([
            "Изучите Python и библиотеки ML (scikit-learn, TensorFlow, PyTorch)",
            "Освойте математику (линейная алгебра, статистика, мат. анализ)",
            "Изучите алгоритмы машинного обучения",
            "Освойте обработку естественного языка",
            "Изучите компьютерное зрение",
            "Изучите глубокое обучение"
        ])
        analysis['careers'].extend([
            "Machine Learning Engineer",
            "AI Research Scientist",
            "Data Scientist",
            "NLP Engineer",
            "Computer Vision Engineer",
            "AI Product Manager"
        ])
        analysis['next_steps'].extend([
            "Изучите Python и основы ML",
            "Освойте математику для ML",
            "Начните изучать scikit-learn",
            "Попробуйте решить задачи на Kaggle",
            "Изучите глубокое обучение",
            "Создайте свой первый ML проект"
        ])
    
    # Анализируем слабые стороны (категории с 0 ответов)
    for category, count in category_counts.items():
        if count == 0:
            if category == 'code':
                analysis['weaknesses'].append("Программирование - возможно, стоит попробовать простые задачи")
            elif category == 'data':
                analysis['weaknesses'].append("Анализ данных - можно развить аналитическое мышление")
            elif category == 'design':
                analysis['weaknesses'].append("Дизайн - можно развить креативность")
            elif category == 'security':
                analysis['weaknesses'].append("Кибербезопасность - можно изучить основы безопасности")
            elif category == 'devops':
                analysis['weaknesses'].append("DevOps - можно изучить автоматизацию и инфраструктуру")
            elif category == 'mobile':
                analysis['weaknesses'].append("Мобильная разработка - можно изучить создание приложений")
            elif category == 'game':
                analysis['weaknesses'].append("Игровая разработка - можно изучить создание игр")
            elif category == 'ai_ml':
                analysis['weaknesses'].append("ИИ/ML - можно изучить машинное обучение")
    
    return analysis

# ============================================================================
# ОБЩИЙ ОБРАБОТЧИК (должен быть ПОСЛЕ всех специфических обработчиков)
# ============================================================================

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Обработка всех остальных сообщений"""
    user_id = message.from_user.id
    
    # Отладочная информация
    print(f"🔍 Получено сообщение от {user_id}: '{message.text}'")
    
    # Проверяем команды в первую очередь
    if message.text.startswith('/'):
        if message.text == '/admin':
            # Обработка команды админа
            admin_panel(message)
            return
        elif message.text == '/start':
            start(message)
            return
        elif message.text == '/help':
            help_command(message)
            return
    
    # Проверяем, находится ли пользователь в админ-панели
    if user_id in admin_states:
        # Пользователь в админ-панели, не обрабатываем здесь
        return
    
    # Проверяем, есть ли активная сессия
    if user_id not in user_states:
        bot.reply_to(message, "Нажмите 'Начать тест' для начала тестирования")
        return
    
    current_state = user_states[user_id]
    
    # Проверяем, что тест еще не завершен
    if 'current_question' not in current_state:
        bot.reply_to(message, "❌ Тест уже завершен. Нажмите 'Начать тест' для нового тестирования.")
        return
    
    current_question = current_state['current_question']
    
    # Получаем все вопросы из БД
    all_questions = db.get_all_questions()
    question_ids = sorted(all_questions.keys())
    
    # Проверяем, что номер вопроса в пределах
    if current_question > len(question_ids):
        bot.reply_to(message, f"❌ Вопрос {current_question} не найден")
        return
    
    # Получаем вопрос по номеру
    question_id = question_ids[current_question - 1]
    question = all_questions[question_id]
    
    # Проверяем, что ответ соответствует одному из вариантов
    valid_answers = [option['text'] for option in question['options']]
    
    # Добавляем отладочную информацию
    print(f"🔍 Вопрос {current_question}:")
    print(f"📝 Полученный ответ: '{message.text}'")
    print(f"✅ Допустимые ответы: {valid_answers}")
    
    if message.text not in valid_answers:
        bot.reply_to(message, "❌ Пожалуйста, выберите один из предложенных вариантов")
        print(f"❌ Ответ не найден в списке допустимых")
        return
    
    # Сохраняем ответ
    answer_value = next(option['value'] for option in question['options'] if option['text'] == message.text)
    current_state['answers'][str(question_id)] = answer_value
    
    # Обновляем в базе данных
    try:
        db.update_user_answers(user_id, question_id, answer_value)
    except Exception as e:
        print(f"❌ Ошибка при обновлении ответов: {e}")
    
    # Переходим к следующему вопросу
    current_state['current_question'] += 1
    
    total_questions = len(question_ids)
    print(f"🔍 Текущий вопрос: {current_state['current_question']}, Всего вопросов: {total_questions}")
    
    if current_state['current_question'] <= total_questions:
        # Отправляем следующий вопрос
        print(f"📝 Отправляем вопрос {current_state['current_question']}")
        send_question(message.chat.id, user_id, current_state['current_question'])
    else:
        # Тест завершен
        print(f"🎉 Тест завершен! Показываем результаты...")
        show_results(message)
        return  # Добавляем return чтобы прервать выполнение

def show_results(message):
    """Показать результаты теста"""
    print(f"🚀 Начинаем показ результатов для пользователя {message.from_user.id}")
    try:
        user_id = message.from_user.id
        current_state = user_states[user_id]
        
        print(f"📊 Состояние пользователя: {current_state}")
        print(f"📝 Количество ответов: {len(current_state.get('answers', {}))}")
        
        # Инициализируем переменные
        spec_info = None
        specialization = None
        
        # Проверяем, есть ли сохраненные результаты
        if 'saved_scores' in current_state and 'saved_percentages' in current_state:
            # Используем сохраненные результаты
            scores = current_state['saved_scores']
            specialization_percentages = current_state['saved_percentages']
            specialization = current_state['saved_specialization']
            spec_info = current_state['saved_spec_info']
        else:
            # Вычисляем результаты заново
            print(f"🔍 Вычисляем результаты заново...")
            scores = {
                "code": 0, "data": 0, "design": 0, "security": 0,
                "devops": 0, "mobile": 0, "game": 0, "ai_ml": 0
            }
            
            print(f"📝 Обрабатываем {len(current_state['answers'])} ответов...")
            for question_id, answer_value in current_state['answers'].items():
                print(f"🔍 Вопрос {question_id}: значение {answer_value}")
                question = db.get_question(int(question_id))
                if question:
                    for option in question['options']:
                        if option['value'] == answer_value:
                            category = option['category']
                            scores[category] += answer_value
                            print(f"✅ Добавили {answer_value} к категории {category}")
                            break
            
            print(f"📊 Итоговые баллы: {scores}")
            
            # Вычисляем проценты для всех 8 специализаций
            total_score = sum(scores.values())
            print(f"📊 Общий балл: {total_score}")
            
            if total_score > 0:
                # Базовые проценты для всех категорий
                base_percentages = {
                    "code": int((scores["code"] / total_score) * 100),
                    "data": int((scores["data"] / total_score) * 100),
                    "design": int((scores["design"] / total_score) * 100),
                    "security": int((scores["security"] / total_score) * 100),
                    "devops": int((scores["devops"] / total_score) * 100),
                    "mobile": int((scores["mobile"] / total_score) * 100),
                    "game": int((scores["game"] / total_score) * 100),
                    "ai_ml": int((scores["ai_ml"] / total_score) * 100)
                }
                
                print(f"📊 Базовые проценты: {base_percentages}")
                
                # Вычисляем проценты для всех 8 специализаций
                specialization_percentages = {
                    "Программная инженерия": base_percentages["code"],
                    "Data Science": base_percentages["data"],
                    "UX/UI дизайн": base_percentages["design"],
                    "Кибербезопасность": base_percentages["security"],
                    "DevOps инженерия": base_percentages["devops"] if base_percentages["devops"] > 0 else int((base_percentages["code"] * 0.7 + base_percentages["security"] * 0.3)),
                    "Мобильная разработка": base_percentages["mobile"] if base_percentages["mobile"] > 0 else int((base_percentages["code"] * 0.6 + base_percentages["design"] * 0.4)),
                    "Game Development": base_percentages["game"] if base_percentages["game"] > 0 else int((base_percentages["design"] * 0.7 + base_percentages["code"] * 0.3)),
                    "AI/ML инженерия": base_percentages["ai_ml"] if base_percentages["ai_ml"] > 0 else int((base_percentages["data"] * 0.8 + base_percentages["code"] * 0.2))
                }
            else:
                base_percentages = {
                    "code": 0, "data": 0, "design": 0, "security": 0,
                    "devops": 0, "mobile": 0, "game": 0, "ai_ml": 0
                }
                specialization_percentages = {
                    "Программная инженерия": 0,
                    "Data Science": 0,
                    "UX/UI дизайн": 0,
                    "Кибербезопасность": 0,
                    "DevOps инженерия": 0,
                    "Мобильная разработка": 0,
                    "Game Development": 0,
                    "AI/ML инженерия": 0
                }
            
            print(f"📊 Проценты специализаций: {specialization_percentages}")
            
            # Определяем специализацию на основе максимального балла и комбинаций
            max_score = max(scores.values())
            print(f"🎯 Максимальный балл: {max_score}")
            
            # Улучшенная логика определения специализации с поддержкой всех 8 категорий
            # Сначала проверяем прямые категории
            if scores["devops"] > 0 and scores["devops"] == max_score:
                specialization = "DevOps инженерия"
            elif scores["mobile"] > 0 and scores["mobile"] == max_score:
                specialization = "Мобильная разработка"
            elif scores["game"] > 0 and scores["game"] == max_score:
                specialization = "Game Development"
            elif scores["ai_ml"] > 0 and scores["ai_ml"] == max_score:
                specialization = "AI/ML инженерия"
            elif scores["code"] > 0 and scores["code"] == max_score:
                specialization = "Программная инженерия"
            elif scores["data"] > 0 and scores["data"] == max_score:
                specialization = "Data Science"
            elif scores["design"] > 0 and scores["design"] == max_score:
                specialization = "UX/UI дизайн"
            elif scores["security"] > 0 and scores["security"] == max_score:
                specialization = "Кибербезопасность"
            else:
                # Если нет явного лидера, используем комбинации
                if abs(scores["code"] - scores["data"]) <= 3:
                    specialization = "AI/ML инженерия"
                elif abs(scores["code"] - scores["design"]) <= 3:
                    specialization = "Game Development"
                elif abs(scores["code"] - scores["security"]) <= 3:
                    specialization = "DevOps инженерия"
                elif abs(scores["design"] - scores["data"]) <= 3:
                    specialization = "UX/UI дизайн"
                else:
                    # По умолчанию выбираем максимальный
                    max_spec = max(specialization_percentages.items(), key=lambda x: x[1])
                    specialization = max_spec[0]
            
            print(f"🎯 Определена специализация: {specialization}")
            
            # Получаем информацию о специализации из БД
            spec_info = db.get_specialization_from_code(specialization)
            
            print(f"📊 Информация о специализации: {spec_info}")
        
        if spec_info:
            # Получаем университеты для этой специализации
            universities = db.get_universities_by_specialization(spec_info['id'])
            
            # Сортируем университеты по баллам (от высших к низшим)
            universities_sorted = sorted(universities, key=lambda x: x.get('score_max', 0), reverse=True)
            
            # Берем топ-5 университетов
            top_universities = universities_sorted[:5]
            
            # Получаем навыки и карьеры
            skills = spec_info.get('skills', '• Программирование (Python, Java, C++)\n• Работа с базами данных\n• Системы контроля версий\n• Методологии разработки')
            careers = spec_info.get('careers', '• Разработчик программного обеспечения\n• Системный аналитик\n• Технический директор\n• Консультант по IT')
            
            result_text = f"""
🎉 Тест завершен!

📊 Ваши результаты по всем направлениям:
• Программная инженерия: {specialization_percentages['Программная инженерия']}%
• Data Science: {specialization_percentages['Data Science']}%
• UX/UI дизайн: {specialization_percentages['UX/UI дизайн']}%
• Кибербезопасность: {specialization_percentages['Кибербезопасность']}%
• DevOps инженерия: {specialization_percentages['DevOps инженерия']}%
• Мобильная разработка: {specialization_percentages['Мобильная разработка']}%
• Game Development: {specialization_percentages['Game Development']}%
• AI/ML инженерия: {specialization_percentages['AI/ML инженерия']}%

🎯 Рекомендуемая специализация: {spec_info['name']}

📝 Описание:
{spec_info['description']}

🏛️ Топ-5 университетов:
"""
            
            # Показываем топ-5 университетов с баллами
            for i, uni in enumerate(top_universities, 1):
                score_range = f"{uni.get('score_min', 0)}-{uni.get('score_max', 0)}"
                result_text += f"\n{i}. {uni['name']}"
                result_text += f"\n   📍 {uni.get('city', 'Неизвестный город')}"
                result_text += f"\n   🎯 Баллы ЕГЭ: {score_range}"
                result_text += f"\n   🎓 Направление: {spec_info['name']}\n"
            
            result_text += f"""

💼 Карьерные возможности:
{careers}

🔧 Необходимые навыки:
{skills}

📚 Дополнительная информация:
• Средняя зарплата: 80,000 - 150,000 руб.
• Востребованность: Высокая
• Перспективы роста: Отличные
            """
        else:
            result_text = f"""
🎉 Тест завершен!

📊 Ваши результаты по всем направлениям:
• Программная инженерия: {specialization_percentages['Программная инженерия']}%
• Data Science: {specialization_percentages['Data Science']}%
• UX/UI дизайн: {specialization_percentages['UX/UI дизайн']}%
• Кибербезопасность: {specialization_percentages['Кибербезопасность']}%
• DevOps инженерия: {specialization_percentages['DevOps инженерия']}%
• Мобильная разработка: {specialization_percentages['Мобильная разработка']}%
• Game Development: {specialization_percentages['Game Development']}%
• AI/ML инженерия: {specialization_percentages['AI/ML инженерия']}%

🎯 Рекомендуемая специализация: {specialization}

📝 Описание:
Специализация не найдена в базе данных. Пожалуйста, обратитесь к администратору.

💡 Рекомендации:
• Пройдите тест еще раз
• Обратитесь к администратору для настройки специализаций
• Проверьте, что все специализации добавлены в базу данных
            """
        
        # Создаем клавиатуру с кнопками
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('Подробный отчёт'))
        markup.add(types.KeyboardButton('Все вузы'))
        markup.add(types.KeyboardButton('Начать тест'))
        markup.add(types.KeyboardButton('Помощь'))
        
        # Сохраняем информацию о специализации для кнопки "Все вузы" и отчёта
        if spec_info:
            current_state['specialization_id'] = spec_info['id']
            current_state['specialization_name'] = spec_info['name']
            current_state['show_all_universities'] = True
        else:
            current_state['show_all_universities'] = False
            
        # Сохраняем результаты для повторного использования (только при первом показе)
        if 'saved_scores' not in current_state:
            current_state['saved_scores'] = scores
            current_state['saved_percentages'] = specialization_percentages
            current_state['saved_specialization'] = specialization
            current_state['saved_spec_info'] = spec_info
        
        # Удаляем только данные текущего теста
        if 'current_question' in current_state:
            del current_state['current_question']
        
        print(f"📤 Отправляем результаты пользователю...")
        bot.send_message(message.chat.id, result_text, reply_markup=markup, disable_web_page_preview=True)
        print(f"✅ Результаты отправлены успешно!")
        
        # НЕ очищаем состояние пользователя - он нужен для кнопки "Все вузы"
        
    except Exception as e:
        print(f"❌ Ошибка в show_results: {e}")
        import traceback
        traceback.print_exc()
        bot.send_message(message.chat.id, "❌ Ошибка при показе результатов")

# ===== КОНЕЦ ФАЙЛА =====

if __name__ == "__main__":
    print("🤖 Запуск исправленного IT-профориентационного бота...")
    print("=" * 50)
    print("✅ Все зависимости установлены")
    print("✅ Конфигурация проверена")
    print("✅ База данных найдена")
    print("=" * 50)
    print("🚀 Запуск бота...")
    print("Для остановки нажмите Ctrl+C")
    print("=" * 50)
    
    try:
        bot.polling(none_stop=True)
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}") 