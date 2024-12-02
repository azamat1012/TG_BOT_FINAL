import logging
from telebot import TeleBot
import django
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bot_backend.settings")
django.setup()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

try:
    from event_planner.models import Speaker, Question, User, Organizer
    from event_planner.utils import get_schedule, get_user_role, remove_expired_speakers
    from event_planner.helpers import create_inline_keyboard, create_reply_keyboard, is_ask_question_command, is_about_command, is_sent_donat, is_speaker_selected, is_speaker_selected_state, is_view_questions_command, user_states
except Exception as e:
    logger.error(f"Error importing models: {e}")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = TeleBot(TELEGRAM_BOT_TOKEN)


def main():
    
    logger.info("Bot main function started.")

    @bot.message_handler(commands=['start'])
    def start(message):
        logger.info(f"""Start command received from {
                    message.chat.id}""")  # Log received command
        tg_id = str(message.chat.id)
        username = message.from_user.username
        try:
            user, created = User.objects.get_or_create(
                tg_id=tg_id,
                defaults={
                    'first_name': message.from_user.first_name,
                    'last_name': message.from_user.last_name,
                    'username': username,
                }
            )
            user.role = get_user_role(tg_id, username) or 'listener'
            user.save()
            keyboard = create_reply_keyboard(user.role)
            role_name = 'Докладчик' if user.role == 'speaker' else 'Слушатель'
            bot.send_message(
                message.chat.id,
                f"""Добро пожаловать, {user.first_name}!\nСейчас Вы - {role_name}  ＼(＾▽＾)／
                    \nДанный бот отвечает за взаимодействие между Докладчиком и Слушателем\n\n               ---------Функциональные возможности--------- \n\n🎤:\nДокладчик может просматривать вопросы, которые
                    он получил от Слушателей.\n🧏‍♂️:\nСлушатель может задавать вопросы выступающему Спикеру, посмореть программу мероприятия и при желании задонатить💸. \n\nПользуйтесь кнопками ниже))\n(Спойлер: это удобно)
                    """,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            bot.send_message(message.chat.id, f"Ошибка при идентификации: {e}")

    @bot.message_handler(func=is_about_command)
    def handle_about(message):
        """Выдача программы"""
        try:
            schedule = get_schedule()
            bot.send_message(message.chat.id, f"{schedule}\n")
        except Exception as e:
            bot.send_message(
                message.chat.id, f"Ошибка при получении расписания: {e}")

    @bot.message_handler(func=is_ask_question_command)
    def question_address(message):
        """Обработка выбора докладчика"""
        tg_id = str(message.chat.id)
        speakers = Speaker.objects.all()
        if not speakers.exists():
            bot.send_message(
                message.chat.id,
                "Извините, на данный момент нет доступных докладчиков. ʕಠᴥಠʔ"
            )
            return

        bot.send_message(
            message.chat.id,
            "Пожалуйста, выберите, кому Вы хотите задать вопрос? \nʕ ᵔᴥᵔ ʔ"
        )
        keyboard = create_inline_keyboard(speakers)
        bot.send_message(
            message.chat.id,
            "Выберите докладчика",
            reply_markup=keyboard
        )
        user_states[tg_id] = 'speaker_selected'

    @bot.callback_query_handler(func=is_speaker_selected)
    def handle_speaker_selected(call):
        """Обработка выбранного Слушателем id Докладчика"""
        tg_id = str(call.message.chat.id)
        try:
            speaker = Speaker.objects.filter(tg_id=call.data).first()
            if not speaker:
                raise ValueError("Нет такого докладчика")

            user_states[tg_id] = {
                'state': 'speaker_selected',
                'speaker_id': call.data
            }
            bot.send_message(
                call.message.chat.id,
                f"""Вы выбрали {
                    speaker.name}.\nТеперь пожалуйста, введите ваш вопрос. ʕ ᵔᴥᵔ ʔ"""
            )
        except ValueError:
            bot.send_message(
                call.message.chat.id,
                "Выбрана некорректная кнопка. Попробуйте снова."
            )
            user_states.pop(tg_id, None)

    @bot.message_handler(func=is_speaker_selected_state)
    def save_question(message):
        """Сохранение вопроса Слушателя и передача его Докладчику"""
        tg_id = str(message.chat.id)
        user_state = user_states.get(tg_id)
        if not user_state or 'speaker_id' not in user_state:
            bot.send_message(
                message.chat.id, "Произошла ошибка. Попробуйте еще раз.")
            return

        speaker_id = user_state['speaker_id']
        user = User.objects.filter(tg_id=tg_id).first()
        speaker = Speaker.objects.filter(tg_id=speaker_id).first()

        if speaker:
            Question.objects.create(
                user=user, speaker=speaker, text=message.text)
            bot.send_message(message.chat.id, "Ваш вопрос отправлен. (っ ᵔᴥᵔ)っ")

        else:
            bot.send_message(
                message.chat.id, "Докладчик не найден. Пожалуйста, попробуйте снова."
            )
        user_states.pop(tg_id, None)

    @bot.message_handler(func=is_view_questions_command)
    def view_questions(message):
        """
        Показывает вопросы для докладчиков
        """
        speaker = Speaker.objects.filter(
            tg_id=f"@{message.from_user.username}").first()

        questions = Question.objects.filter(
            speaker=speaker).order_by('-created_at')
        if questions.exists():
            response = "Ваши вопросы:\n\n" + "\n".join(
                [f"{q.user.first_name}: {q.text}" for q in questions]
            )
        else:
            response = "У вас пока нет вопросов."
        bot.send_message(message.chat.id, response)

    @bot.message_handler(func=is_sent_donat)
    def send_donat(message):
        """Отпраавляет донат"""
        try:
            speaker = Organizer.objects.all().first()

            bot.send_message(
                message.chat.id,
                f"""Спасибо за вашу поддержку!૮ ˶ᵔ ᵕ ᵔ˶ ა\nВы можете отправить донат по следующему реквизитам карты:\n{
                    speaker.card_num}"""
            )

        except Exception as e:
            bot.send_message(
                message.chat.id,
                "Извините, номер карты спикера не указан. ┐( ˘_˘ )┌"
            )
        except Speaker.DoesNotExist:
            bot.send_message(
                message.chat.id,
                "Извините, информация о спикере не найдена.{{ (>_<) }}"
            )
    logger.info("Bot is polling...")  
    bot.polling(non_stop=True, interval=0)  


if __name__ == "__main__":
    logger.info("Bot script started.")  
    main()  
