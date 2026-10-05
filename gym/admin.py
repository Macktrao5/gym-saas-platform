from django.contrib import admin
from .models import Palestra, Attrezzo, CorsoOnline, CategoriaAttrezzo, OrarioApertura, PersonalTrainer, PrenotazioneContatto
from .models import Abbonamento
from .models import SubscriptionPlan, UserSubscription
from .models import WorkoutPlan, WorkoutExercise
from .models import CourseBooking, UserProgress
from .models import DietPlan
from .models import UserBadge
from .models import VideoLesson
from .models import Notification
from .models import SmsWhatsappLog, GymEquipment
from .models import MemberPass, UserProfile
from .models import GymCourse, CourseBooking
from .models import SlotOrario, PrenotazioneCorso
from .models import Recensione

admin.site.register(GymCourse)
admin.site.register(Abbonamento)
admin.site.register(OrarioApertura)
admin.site.register(PrenotazioneContatto)
admin.site.register(PersonalTrainer)
@admin.register(Palestra)
class PalestraAdmin(admin.ModelAdmin):
    list_display = ('nome', 'citta', 'telefono')
    prepopulated_fields = {'slug': ('nome',)}

@admin.register(CategoriaAttrezzo)
class CategoriaAttrezzoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'descrizione')
    search_fields = ('nome',)


@admin.register(Attrezzo)
class AttrezzoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'palestra', 'categoria', 'muscoli_coinvolti')
    list_filter = ('categoria', 'palestra')
    search_fields = ('nome', 'muscoli_coinvolti')

@admin.register(CorsoOnline)
class CorsoOnlineAdmin(admin.ModelAdmin):
    list_display = ('title', 'max_capacity', 'current_booked')
    list_filter = ('max_capacity',)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'gym', 'duration_days', 'price')
    list_filter = ('gym',)

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'plan__gym')

class WorkoutExerciseInline(admin.TabularInline):
    model = WorkoutExercise
    extra = 1

@admin.register(WorkoutPlan)
class WorkoutPlanAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at', 'is_active')
    search_fields = ('title', 'user__username', 'user__email')
    list_filter = ('is_active', 'created_at')
    inlines = [WorkoutExerciseInline]


@admin.register(CourseBooking)
class CourseBookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'booking_date', 'status')
    list_filter = ('status', 'booking_date')
    search_fields = ('user__username', 'course__title')

@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'weight', 'body_fat', 'muscle_mass')
    list_filter = ('date',)
    search_fields = ('user__username',)



@admin.register(DietPlan)
class DietPlanAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at', 'is_active')
    search_fields = ('user__username', 'title')




@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'icon_emoji', 'date_earned')
    search_fields = ('user__username', 'title')




@admin.register(VideoLesson)
class VideoLessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'duration', 'created_at')
    search_fields = ('title', 'instructor')





@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    list_filter = ('is_read', 'created_at')




@admin.register(SmsWhatsappLog)
class SmsWhatsappLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'channel', 'message_type', 'phone_number', 'sent_at', 'status')
    search_fields = ('user__username', 'phone_number', 'message_type')
    list_filter = ('channel', 'status', 'sent_at')

@admin.register(GymEquipment)
class GymEquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'status', 'last_check_date')
    search_fields = ('name', 'category')
    list_filter = ('category', 'status')


@admin.register(MemberPass)
class MemberPassAdmin(admin.ModelAdmin):
    list_display = ('user', 'pass_code', 'serial_number', 'is_active')
    search_fields = ('user__username', 'pass_code', 'serial_number')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'medical_certificate_expiry')
    search_fields = ('user__username', 'user__email')




@admin.register(SlotOrario)
class SlotOrarioAdmin(admin.ModelAdmin):
    list_display = ('corso', 'giorno_settimana', 'ora_inizio', 'ora_fine', 'posti_disponibili')
    list_filter = ('giorno_settimana', 'corso')

@admin.register(PrenotazioneCorso)
class PrenotazioneCorsoAdmin(admin.ModelAdmin):
    list_display = ('utente', 'slot', 'data_prenotazione')
    list_filter = ('slot__corso', 'data_prenotazione')
    search_fields = ('utente__username', 'slot__corso__nome')





@admin.register(Recensione)
class RecensioneAdmin(admin.ModelAdmin):
    list_display = ('palestra', 'utente', 'valutazione', 'data_creazione')
    list_filter = ('valutazione', 'data_creazione', 'palestra')
    search_fields = ('utente__username', 'palestra__nome', 'commento')