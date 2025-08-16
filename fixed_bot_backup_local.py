import json
import os
import sys
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple

from sqlalchemy import Column, Integer, String, ForeignKey, create_engine, func, select, distinct
from sqlalchemy.orm import declarative_base, relationship, Session

try:
	import telebot
except ImportError:
	print("pyTelegramBotAPI is not installed. Run: pip install pyTelegramBotAPI")
	sys.exit(1)

try:
	from config import BOT_TOKEN, ADMIN_IDS
except Exception:
	print("config.py is missing or invalid. Please create config.py with BOT_TOKEN and ADMIN_IDS.")
	sys.exit(1)


# ---------------------------
# Database setup
# ---------------------------
Base = declarative_base()

DB_DIR = os.path.join(os.getcwd(), "database")
DB_PATH = os.path.join(DB_DIR, "bot_new.db")

if not os.path.isdir(DB_DIR):
	os.makedirs(DB_DIR, exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)


class Specialization(Base):
	__tablename__ = "specializations"

	id = Column(Integer, primary_key=True)
	name = Column(String, unique=True, nullable=False)
	description = Column(String, nullable=True)

	universities = relationship("University", back_populates="specialization")


class University(Base):
	__tablename__ = "universities"

	id = Column(Integer, primary_key=True)
	name = Column(String, nullable=False)
	city = Column(String, nullable=True)
	score_min = Column(Integer, nullable=True)
	score_max = Column(Integer, nullable=True)
	url = Column(String, nullable=True)
	specialization_id = Column(Integer, ForeignKey("specializations.id"), nullable=True)

	specialization = relationship("Specialization", back_populates="universities")


Base.metadata.create_all(engine)


# ---------------------------
# Bootstrap data from JSON (if DB is empty)
# ---------------------------
SPECIALIZATIONS_JSON = os.path.join(os.getcwd(), "specializations.json")
UNIVERSITIES_JSON = os.path.join(os.getcwd(), "universities.json")


def bootstrap_from_json_if_needed() -> None:
	with Session(engine) as session:
		# Specializations
		count_specs = session.scalar(select(func.count(Specialization.id))) or 0
		if count_specs == 0 and os.path.isfile(SPECIALIZATIONS_JSON):
			try:
				data = json.load(open(SPECIALIZATIONS_JSON, "r", encoding="utf-8"))
				for item in data:
					name = item.get("name")
					description = item.get("description")
					if name:
						session.add(Specialization(name=name, description=description))
				session.commit()
			except Exception as e:
				print(f"Failed to import specializations.json: {e}")

		# Universities
		count_unis = session.scalar(select(func.count(University.id))) or 0
		if count_unis == 0 and os.path.isfile(UNIVERSITIES_JSON):
			try:
				data = json.load(open(UNIVERSITIES_JSON, "r", encoding="utf-8"))
				# expected format: list of entries with name, city, score_min, score_max, url, specialization
				# specialization may be either name or id; we try name first
				name_to_spec_id: Dict[str, int] = {}
				for spec in session.scalars(select(Specialization)).all():
					name_to_spec_id[spec.name.strip().lower()] = spec.id

				for item in data:
					name = item.get("name")
					city = item.get("city") or item.get("location")
					score_min = item.get("score_min")
					score_max = item.get("score_max")
					url = item.get("url") or item.get("link")
					spec_name = item.get("specialization") or item.get("speciality") or item.get("spec")
					specialization_id = None
					if isinstance(spec_name, str):
						key = spec_name.strip().lower()
						specialization_id = name_to_spec_id.get(key)
					elif isinstance(spec_name, int):
						specialization_id = spec_name
					if name:
						session.add(University(
							name=name,
							city=city,
							score_min=to_int_or_none(score_min),
							score_max=to_int_or_none(score_max),
							url=url,
							specialization_id=specialization_id
						))
				session.commit()
			except Exception as e:
				print(f"Failed to import universities.json: {e}")


def to_int_or_none(v):
	try:
		if v is None or v == "":
			return None
		return int(v)
	except Exception:
		return None


# ---------------------------
# Query helpers
# ---------------------------

def get_unique_university_names(session: Session) -> List[str]:
	rows = session.execute(select(distinct(University.name)).order_by(University.name)).all()
	return [r[0] for r in rows if r[0]]


def get_unique_universities_page(session: Session, page: int, per_page: int = 10) -> Tuple[List[Tuple[str, Optional[str], Optional[str]]], int]:
	# We will build unique list by name, taking first city/url encountered
	names = get_unique_university_names(session)
	total_pages = max(1, (len(names) + per_page - 1) // per_page)
	page = max(1, min(page, total_pages))
	start = (page - 1) * per_page
	end = start + per_page
	page_names = names[start:end]

	result: List[Tuple[str, Optional[str], Optional[str]]] = []
	for uni_name in page_names:
		row = session.execute(
			select(University.name, University.city, University.url)
			.where(University.name == uni_name)
			.limit(1)
		).first()
		if row:
			result.append((row[0], row[1], row[2]))
	return result, total_pages


def get_stats(session: Session) -> Tuple[int, int]:
	total_records = session.scalar(select(func.count(University.id))) or 0
	unique_unis = session.execute(select(func.count(distinct(University.name)))).scalar_one()
	return int(unique_unis or 0), int(total_records or 0)


def get_specialization_buttons(session: Session) -> List[telebot.types.InlineKeyboardButton]:
	buttons: List[telebot.types.InlineKeyboardButton] = []
	for spec in session.scalars(select(Specialization).order_by(Specialization.name)).all():
		buttons.append(telebot.types.InlineKeyboardButton(text=spec.name, callback_data=f"add_spec:{spec.id}"))
	return buttons


# ---------------------------
# Export DB -> universities.json (sync)
# ---------------------------

def sync_universities_to_json() -> None:
	with Session(engine) as session:
		rows = session.execute(
			select(
				University.name,
				University.city,
				University.score_min,
				University.score_max,
				University.url,
				Specialization.name.label("specialization")
			)
			.select_from(University)
			.join(Specialization, Specialization.id == University.specialization_id, isouter=True)
		).all()

		data = []
		for r in rows:
			data.append({
				"name": r.name,
				"city": r.city,
				"score_min": r.score_min,
				"score_max": r.score_max,
				"url": r.url,
				"specialization": r.specialization
			})

		with open(UNIVERSITIES_JSON, "w", encoding="utf-8") as f:
			json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------
# Telegram bot
# ---------------------------
if not BOT_TOKEN or BOT_TOKEN.startswith("PASTE_"):
	print("Please set a valid BOT_TOKEN in config.py before running the bot.")
	sys.exit(1)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


# ---------------------------
# Test logic (questions, sessions)
# ---------------------------

ANSWER_SCALE = [
	("Нет", 0),
	("Скорее нет", 1),
	("Скорее да", 2),
	("Да", 3),
]

@dataclass
class UserTestSession:
	question_index: int = 0
	scores: Dict[str, int] = None
	finished: bool = False
	last_percentages: Dict[str, int] = None

	def __post_init__(self):
		if self.scores is None:
			self.scores = {}


def load_specialization_names() -> List[str]:
	with Session(engine) as session:
		return [s.name for s in session.scalars(select(Specialization).order_by(Specialization.name)).all()]

SPECIALIZATION_NAMES_CACHE: List[str] = []


def get_questions() -> List[Dict]:
	# Lightweight placeholder set (10 вопросов). Можно расширить до 30.
	global SPECIALIZATION_NAMES_CACHE
	if not SPECIALIZATION_NAMES_CACHE:
		SPECIALIZATION_NAMES_CACHE = load_specialization_names()
	# Каждому вопросу сопоставим веса для специализаций (0..3)
	specs = SPECIALIZATION_NAMES_CACHE or [
		"Программирование",
		"Data Science",
		"AI/ML инженерия",
		"DevOps инженерия",
		"Кибербезопасность",
		"UX/UI дизайн",
		"Мобильная разработка",
	]
	base = [
		{
			"text": "Нравится писать код и решать алгоритмические задачи?",
			"weights": {"Программирование": 3, "Мобильная разработка": 2, "DevOps инженерия": 1}
		},
		{
			"text": "Интересны данные, аналитика и статистика?",
			"weights": {"Data Science": 3, "AI/ML инженерия": 2}
		},
		{
			"text": "Хотите разбираться в нейросетях и моделях?",
			"weights": {"AI/ML инженерия": 3, "Data Science": 2}
		},
		{
			"text": "Нравится автоматизация и CI/CD?",
			"weights": {"DevOps инженерия": 3, "Программирование": 1}
		},
		{
			"text": "Интересуют взлом, защита и протоколы?",
			"weights": {"Кибербезопасность": 3, "DevOps инженерия": 1}
		},
		{
			"text": "Тянет к дизайну интерфейсов и продукту?",
			"weights": {"UX/UI дизайн": 3, "Мобильная разработка": 1}
		},
		{
			"text": "Хочется делать приложения для смартфонов?",
			"weights": {"Мобильная разработка": 3, "Программирование": 2}
		},
		{
			"text": "Предпочитаете математику и эксперименты?",
			"weights": {"Data Science": 2, "AI/ML инженерия": 2}
		},
		{
			"text": "Нравится строить архитектуру систем?",
			"weights": {"Программирование": 2, "DevOps инженерия": 2}
		},
		{
			"text": "Больше про безопасность, чем про фичи?",
			"weights": {"Кибербезопасность": 2, "Программирование": 1}
		},
	]
	# Убедимся, что все ключи существуют в списке специализаций
	for q in base:
		for k in list(q["weights"].keys()):
			if k not in specs:
				del q["weights"][k]
	return base


def calculate_percentages(scores: Dict[str, int]) -> Dict[str, int]:
	if not scores:
		return {}
	max_score = max(scores.values()) if scores else 0
	if max_score == 0:
		return {k: 0 for k in scores}
	# нормируем к 100
	result: Dict[str, int] = {}
	for k, v in scores.items():
		pct = int(round(v * 100 / max_score))
		result[k] = min(100, max(0, pct))
	return result


def create_detailed_report(top_spec: str, percentages: Dict[str, int], scores: Dict[str, int]) -> str:
	lines = [f"Подробный отчёт\n", f"Ваша сильнейшая специализация: <b>{top_spec}</b>\n"]
	if percentages:
		lines.append("Проценты по направлениям:")
		for k, v in sorted(percentages.items(), key=lambda x: -x[1]):
			lines.append(f"• {k}: {v}%")
	lines.append("\nЧто дальше:")
	if top_spec.lower().startswith("программ"):
		lines.append("— Начните с алгоритмов и структур данных, затем фреймворков по интересу.")
	elif "data" in top_spec.lower() or "ai/ml" in top_spec.lower() or "ai" in top_spec.lower():
		lines.append("— Пройдите основы статистики, Python, NumPy/Pandas; затем ML-библиотеки.")
	elif "devops" in top_spec.lower():
		lines.append("— Освойте Linux, Docker, CI/CD, IaC и облачные провайдеры.")
	elif "кибер" in top_spec.lower():
		lines.append("— Изучите сети, протоколы, криптографию, практикуйте CTF.")
	elif "дизайн" in top_spec.lower():
		lines.append("— Прокачайте UX-исследования, дизайн-системы, прототипирование.")
	elif "мобил" in top_spec.lower():
		lines.append("— Выберите iOS/Android, изучите Swift/Kotlin и архитектуры приложений.")
	else:
		lines.append("— Уточняйте интерес: выберите поднаправление и собирайте портфолио.")
	return "\n".join(lines)


# user_id -> session
USER_SESSIONS: Dict[int, UserTestSession] = {}


def start_test(chat_id: int, user_id: int):
	USER_SESSIONS[user_id] = UserTestSession()
	send_question(chat_id, user_id)


def send_question(chat_id: int, user_id: int):
	sess = USER_SESSIONS.get(user_id)
	if not sess:
		USER_SESSIONS[user_id] = UserTestSession()
		sess = USER_SESSIONS[user_id]
	questions = get_questions()
	if sess.question_index >= len(questions):
		return show_results(chat_id, user_id)
	q = questions[sess.question_index]
	kb = telebot.types.InlineKeyboardMarkup()
	for label, weight in ANSWER_SCALE:
		kb.row(telebot.types.InlineKeyboardButton(label, callback_data=f"ans:{weight}"))
	bot.send_message(chat_id, f"Вопрос {sess.question_index+1}/{len(questions)}\n\n{q['text']}", reply_markup=kb)


def handle_answer(user_id: int, weight: int):
	sess = USER_SESSIONS.get(user_id)
	if not sess:
		return
	q = get_questions()[sess.question_index]
	for spec, base_w in q["weights"].items():
		sess.scores[spec] = sess.scores.get(spec, 0) + base_w * weight
	sess.question_index += 1


def show_results(chat_id: int, user_id: int):
	sess = USER_SESSIONS.get(user_id)
	if not sess:
		return
	percentages = calculate_percentages(sess.scores)
	sess.last_percentages = percentages
	top_spec = next(iter(sorted(percentages.items(), key=lambda x: -x[1])), ("—", 0))[0]
	lines = ["Результаты теста:"]
	for k, v in sorted(percentages.items(), key=lambda x: -x[1])[:5]:
		lines.append(f"• {k}: {v}%")
	kb = telebot.types.InlineKeyboardMarkup()
	kb.row(telebot.types.InlineKeyboardButton("Подробный отчёт", callback_data="report"))
	bot.send_message(chat_id, "\n".join(lines), reply_markup=kb)
	sess.finished = True


# ---------------------------
# Commands
# ---------------------------

def is_admin(user_id: int) -> bool:
	return user_id in ADMIN_IDS


@bot.message_handler(commands=["start"]) 
def cmd_start(message: telebot.types.Message):
	text = (
		"Привет! Это IT профориентационный бот.\n\n"
		"Команды:\n"
		"/start_test — пройти тест (≈10 вопросов)\n"
		"/restart — начать заново\n"
		"/universities — список вузов (уникальные)\n"
		"/admin — админ-панель\n"
	)
	bot.reply_to(message, text)


@bot.message_handler(commands=["start_test"]) 
def cmd_start_test(message: telebot.types.Message):
	start_test(message.chat.id, message.from_user.id)


@bot.message_handler(commands=["restart"]) 
def cmd_restart(message: telebot.types.Message):
	USER_SESSIONS.pop(message.from_user.id, None)
	bot.reply_to(message, "Сессия сброшена. Команда: /start_test")


@bot.message_handler(commands=["admin"]) 
def cmd_admin(message: telebot.types.Message):
	if not is_admin(message.from_user.id):
		bot.reply_to(message, "Команда доступна только админам")
		return

	with Session(engine) as session:
		unique_count, total_records = get_stats(session)
		text = (
			"Админ-панель\n\n"
			f"Уникальных вузов: <b>{unique_count}</b>\n"
			f"Всего записей (со специальностями): <b>{total_records}</b>\n"
		)
		kb = telebot.types.InlineKeyboardMarkup()
		kb.row(
			telebot.types.InlineKeyboardButton("Показать вузы", callback_data="admin_show_unis:1"),
			telebot.types.InlineKeyboardButton("Синхронизировать сайт", callback_data="admin_sync")
		)
		kb.row(
			telebot.types.InlineKeyboardButton("Добавить вуз", callback_data="admin_add"),
			telebot.types.InlineKeyboardButton("Удалить вуз", callback_data="admin_delete:1"),
		)
		bot.reply_to(message, text, reply_markup=kb)


@bot.message_handler(commands=["universities"]) 
def cmd_universities(message: telebot.types.Message):
	show_universities_page(message.chat.id, page=1)


def show_universities_page(chat_id: int, page: int):
	with Session(engine) as session:
		rows, total_pages = get_unique_universities_page(session, page)
		if not rows:
			bot.send_message(chat_id, "Список вузов пуст")
			return

		lines = [f"Страница {page}/{total_pages}"]
		for name, city, url in rows:
			city_part = f" ({city})" if city else ""
			if url:
				lines.append(f"• <b>{name}</b>{city_part} — <a href=\"{url}\">сайт</a>")
			else:
				lines.append(f"• <b>{name}</b>{city_part}")

		kb = telebot.types.InlineKeyboardMarkup()
		nav = []
		if page > 1:
			nav.append(telebot.types.InlineKeyboardButton("◀", callback_data=f"unis_page:{page-1}"))
		if page < total_pages:
			nav.append(telebot.types.InlineKeyboardButton("▶", callback_data=f"unis_page:{page+1}"))
		if nav:
			kb.row(*nav)
		bot.send_message(chat_id, "\n".join(lines), reply_markup=kb)


# ---------------------------
# Callback handlers
# ---------------------------
@bot.callback_query_handler(func=lambda c: c.data.startswith("ans:"))
def cb_answer(call: telebot.types.CallbackQuery):
	try:
		weight = int(call.data.split(":")[1])
	except Exception:
		weight = 0
	handle_answer(call.from_user.id, weight)
	bot.answer_callback_query(call.id)
	bot.delete_message(call.message.chat.id, call.message.message_id)
	send_question(call.message.chat.id, call.from_user.id)


@bot.callback_query_handler(func=lambda c: c.data == "report")
def cb_report(call: telebot.types.CallbackQuery):
	sess = USER_SESSIONS.get(call.from_user.id)
	if not sess or not sess.last_percentages:
		bot.answer_callback_query(call.id, "Результатов нет")
		return
	percentages = sess.last_percentages
	top_spec = next(iter(sorted(percentages.items(), key=lambda x: -x[1])), ("—", 0))[0]
	report = create_detailed_report(top_spec, percentages, sess.scores)
	bot.answer_callback_query(call.id)
	bot.send_message(call.message.chat.id, report)


@bot.callback_query_handler(func=lambda c: c.data.startswith("unis_page:"))
def cb_unis_page(call: telebot.types.CallbackQuery):
	page = int(call.data.split(":")[1])
	bot.answer_callback_query(call.id)
	bot.delete_message(call.message.chat.id, call.message.message_id)
	show_universities_page(call.message.chat.id, page)


@bot.callback_query_handler(func=lambda c: c.data == "admin_sync")
def cb_admin_sync(call: telebot.types.CallbackQuery):
	if not is_admin(call.from_user.id):
		bot.answer_callback_query(call.id, "Только для админов")
		return
	sync_universities_to_json()
	bot.answer_callback_query(call.id, "Синхронизировано")


@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_show_unis:"))
def cb_admin_show_unis(call: telebot.types.CallbackQuery):
	if not is_admin(call.from_user.id):
		bot.answer_callback_query(call.id, "Только для админов")
		return
	page = int(call.data.split(":")[1])
	bot.answer_callback_query(call.id)
	bot.delete_message(call.message.chat.id, call.message.message_id)
	show_universities_page(call.message.chat.id, page)


@bot.callback_query_handler(func=lambda c: c.data == "admin_add")
def cb_admin_add(call: telebot.types.CallbackQuery):
	if not is_admin(call.from_user.id):
		bot.answer_callback_query(call.id, "Только для админов")
		return
	user_states[call.from_user.id] = AddUniversityState()
	with Session(engine) as session:
		buttons = get_specialization_buttons(session)
		kb = telebot.types.InlineKeyboardMarkup()
		# place buttons in rows of 2
		row: List[telebot.types.InlineKeyboardButton] = []
		for b in buttons:
			row.append(b)
			if len(row) == 2:
				kb.row(*row)
				row = []
		if row:
			kb.row(*row)
		bot.answer_callback_query(call.id)
		bot.send_message(call.message.chat.id, "Выберите специальность:", reply_markup=kb)


@dataclass
class AddUniversityState:
	specialization_id: Optional[int] = None
	university_name: Optional[str] = None
	city: Optional[str] = None
	score_min: Optional[int] = None
	score_max: Optional[int] = None
	url: Optional[str] = None


user_states: Dict[int, AddUniversityState] = {}


@bot.callback_query_handler(func=lambda c: c.data.startswith("add_spec:"))
def cb_add_spec(call: telebot.types.CallbackQuery):
	if not is_admin(call.from_user.id):
		bot.answer_callback_query(call.id, "Только для админов")
		return
	state = user_states.get(call.from_user.id) or AddUniversityState()
	state.specialization_id = int(call.data.split(":")[1])
	user_states[call.from_user.id] = state
	bot.answer_callback_query(call.id)
	msg = bot.send_message(call.message.chat.id, "Введите название вуза:")
	bot.register_next_step_handler(msg, handle_add_name)


def handle_add_name(message: telebot.types.Message):
	state = user_states.get(message.from_user.id)
	if not state:
		bot.reply_to(message, "Сессия добавления не найдена. Нажмите /admin → Добавить вуз")
		return
	state.university_name = (message.text or "").strip()
	msg = bot.send_message(message.chat.id, "Город (или регион):")
	bot.register_next_step_handler(msg, handle_add_city)


def handle_add_city(message: telebot.types.Message):
	state = user_states.get(message.from_user.id)
	if not state:
		bot.reply_to(message, "Сессия добавления не найдена. Нажмите /admin → Добавить вуз")
		return
	state.city = (message.text or "").strip()
	msg = bot.send_message(message.chat.id, "Минимальный балл (число, можно пропустить):")
	bot.register_next_step_handler(msg, handle_add_score_min)


def handle_add_score_min(message: telebot.types.Message):
	state = user_states.get(message.from_user.id)
	if not state:
		bot.reply_to(message, "Сессия добавления не найдена. Нажмите /admin → Добавить вуз")
		return
	state.score_min = to_int_or_none(message.text)
	msg = bot.send_message(message.chat.id, "Максимальный балл (число, можно пропустить):")
	bot.register_next_step_handler(msg, handle_add_score_max)


def handle_add_score_max(message: telebot.types.Message):
	state = user_states.get(message.from_user.id)
	if not state:
		bot.reply_to(message, "Сессия добавления не найдена. Нажмите /admin → Добавить вуз")
		return
	state.score_max = to_int_or_none(message.text)
	msg = bot.send_message(message.chat.id, "URL (ссылка на страницу, можно пропустить):")
	bot.register_next_step_handler(msg, handle_add_url)


def handle_add_url(message: telebot.types.Message):
	state = user_states.get(message.from_user.id)
	if not state:
		bot.reply_to(message, "Сессия добавления не найдена. Нажмите /admin → Добавить вуз")
		return
	state.url = (message.text or "").strip() or None

	# Save to DB
	with Session(engine) as session:
		try:
			uni = University(
				name=state.university_name,
				city=state.city,
				score_min=state.score_min,
				score_max=state.score_max,
				url=state.url,
				specialization_id=state.specialization_id,
			)
			session.add(uni)
			session.commit()
		except Exception as e:
			bot.reply_to(message, f"Ошибка при сохранении: {e}")
			return

	# Sync to JSON
	sync_universities_to_json()

	bot.reply_to(message, "Вуз добавлен и сайт синхронизирован.")
	user_states.pop(message.from_user.id, None)


@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_delete:"))
def cb_admin_delete(call: telebot.types.CallbackQuery):
	if not is_admin(call.from_user.id):
		bot.answer_callback_query(call.id, "Только для админов")
		return
	page = int(call.data.split(":")[1])
	with Session(engine) as session:
		names = get_unique_university_names(session)
		per_page = 10
		total_pages = max(1, (len(names) + per_page - 1) // per_page)
		page = max(1, min(page, total_pages))
		start = (page - 1) * per_page
		end = start + per_page
		page_names = names[start:end]

		kb = telebot.types.InlineKeyboardMarkup()
		for n in page_names:
			kb.row(telebot.types.InlineKeyboardButton(n, callback_data=f"delete_by_name:{n}"))
		nav = []
		if page > 1:
			nav.append(telebot.types.InlineKeyboardButton("◀", callback_data=f"admin_delete:{page-1}"))
		if page < total_pages:
			nav.append(telebot.types.InlineKeyboardButton("▶", callback_data=f"admin_delete:{page+1}"))
		if nav:
			kb.row(*nav)
		bot.answer_callback_query(call.id)
		bot.edit_message_text(
			chat_id=call.message.chat.id,
			message_id=call.message.message_id,
			text=f"Удаление вузов. Стр. {page}/{total_pages}",
			reply_markup=kb
		)


@bot.callback_query_handler(func=lambda c: c.data.startswith("delete_by_name:"))
def cb_delete_by_name(call: telebot.types.CallbackQuery):
	if not is_admin(call.from_user.id):
		bot.answer_callback_query(call.id, "Только для админов")
		return
	name = call.data.split(":", 1)[1]
	with Session(engine) as session:
		try:
			session.query(University).filter(University.name == name).delete(synchronize_session=False)
			session.commit()
		except Exception as e:
			bot.answer_callback_query(call.id, f"Ошибка: {e}")
			return
	sync_universities_to_json()
	bot.answer_callback_query(call.id, "Удалено и синхронизировано")
	bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"Удалено: {name}")


# ---------------------------
# Startup
# ---------------------------
bootstrap_from_json_if_needed()

print("[BOT] Removing webhook (if any) ...")
try:
	bot.remove_webhook()
except Exception:
	pass
print("[BOT] Starting polling ...")
try:
	bot.polling(none_stop=True, interval=0, timeout=20)
except KeyboardInterrupt:
	print("Stopped by user") 