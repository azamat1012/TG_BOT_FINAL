import os
from django.contrib import admin
from event_planner.models import Event, Speaker, Session, SpeakerSession, User, Question, Organizer
from event_planner.utils import get_schedule
from telebot import TeleBot


TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'location')
    search_fields = ('name', 'location')
    list_filter = ('date',)
    ordering = ('date',)


@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    list_display = ('name', 'stack')
    search_fields = ('name', 'stack')
    ordering = ('name',)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'event')
    search_fields = ('title', 'event__name')
    list_filter = ('event',)
    ordering = ('event__date',)


@admin.register(SpeakerSession)
class SpeakerSessionAdmin(admin.ModelAdmin):
    list_display = ('speaker', 'topic', )
    search_fields = ('speaker__name', 'topic')
    ordering = ('session__event__date',)


@admin.action(description="Рассылка о изменении в расписании")
def send_massage_to_all_users(modeladmin, request, queryset):
    bot = TeleBot(TELEGRAM_BOT_TOKEN)
    users = User.objects.all()
    massage_text = get_schedule()

    for user in users:
        try:
            bot.send_message(user.tg_id, massage_text)
        except Exception:
            pass
    modeladmin.message_user(
        request, "Сообщения отправлены всем пользователям!")


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    actions = [send_massage_to_all_users]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('speaker__name', 'created_at', 'user__first_name')
    search_fields = ('speaker__name', 'created_at')
    list_filter = ('speaker__name',)
    ordering = ('speaker__name',)


@admin.register(Organizer)
class OrganizerAdmin(admin.ModelAdmin):
    list_display = ('card_num',)
    list_filter = ('card_num',)
    ordering = ('card_num',)
