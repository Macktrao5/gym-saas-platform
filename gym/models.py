from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
from django.contrib.auth.models import User

class Palestra(models.Model):
    nome = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, help_text="Identificativo univoco per l'URL, es. fit-club-barletta")
    citta = models.CharField(max_length=100)
    indirizzo = models.CharField(max_length=255)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    logo = models.ImageField(upload_to='palestre/loghi/', blank=True, null=True)
    immagine_copertina = models.ImageField(upload_to='palestre/copertine/', blank=True, null=True)
    descrizione_breve = models.TextField(blank=True, null=True)
    
    
    def __str__(self):
        return f"{self.nome} ({self.citta})"


class CategoriaAttrezzo(models.Model):
    nome = models.CharField(max_length=100)
    descrizione = models.TextField(blank=True, null=True)
    immagine = models.ImageField(upload_to='categorie_attrezzi/', blank=True, null=True) # <-- Aggiunto qui

    def __str__(self):
        return self.nome


class Attrezzo(models.Model):
    palestra = models.ForeignKey(Palestra, on_delete=models.CASCADE, related_name='attrezzi')
    categoria = models.ForeignKey(CategoriaAttrezzo, on_delete=models.SET_NULL, null=True, blank=True)
    nome = models.CharField(max_length=150)
    descrizione = models.TextField()
    muscoli_coinvolti = models.CharField(max_length=255, help_text="Es. Petto, Tricipiti, Spalle")
    immagine = models.ImageField(upload_to='attrezzi/', blank=True, null=True)

    def __str__(self):
        return f"{self.nome} - {self.palestra.nome}"


class CorsoOnline(models.Model):
    # ... i campi esistenti del tuo CorsoOnline (title, instructor, ecc.) ...
    title = models.CharField(max_length=100)
    # Eventuali altri campi che già possiedi...
    max_capacity = models.IntegerField(default=15)
    current_booked = models.IntegerField(default=0)

    @property
    def available_spots(self):
        return self.max_capacity - self.current_booked

    
class Abbonamento(models.Model):
    palestra = models.ForeignKey(Palestra, on_delete=models.CASCADE, related_name='abbonamenti')
    nome_piano = models.CharField(max_length=100) # Es. "Full Open Mensile", "Sala Pesi Base"
    prezzo = models.DecimalField(max_digits=6, decimal_places=2) # Es. 45.00
    durata = models.CharField(max_length=50) # Es. "1 Mese", "3 Mesi", "Annuale"
    descrizione = models.TextField()
    caratteristiche = models.TextField(help_text="Inserisci le caratteristiche separate da virgola o punto")
    
    def __str__(self):
        return f"{self.nome_piano} - {self.palestra.nome}"

class OrarioApertura(models.Model):
    palestra = models.ForeignKey(Palestra, on_delete=models.CASCADE, related_name='orari')
    GIORNI_CHOICES = [
        ('Lunedì', 'Lunedì'),
        ('Martedì', 'Martedì'),
        ('Mercoledì', 'Mercoledì'),
        ('Giovedì', 'Giovedì'),
        ('Venerdì', 'Venerdì'),
        ('Sabato', 'Sabato'),
        ('Domenica', 'Domenica'),
    ]
    giorno = models.CharField(max_length=20, choices=GIORNI_CHOICES)
    orario_apertura = models.CharField(max_length=50) # Es. "08:00 - 22:00" o "Chiuso"
    chiuso = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.giorno}: {'Chiuso' if self.chiuso else self.orario_apertura} - {self.palestra.nome}"

class PersonalTrainer(models.Model):
    palestra = models.ForeignKey(Palestra, on_delete=models.CASCADE, related_name='trainers')
    nome = models.CharField(max_length=100)
    specializzazione = models.CharField(max_length=150) # Es. "Bodybuilding & Powerlifting", "Rieducazione Posturale"
    bio = models.TextField(blank=True, null=True)
    foto = models.ImageField(upload_to='trainers/', blank=True, null=True)
    giorni_disponibili = models.CharField(max_length=100) # Es. "Lunedì, Mercoledì, Venerdì"

    def __str__(self):
        return f"{self.nome} ({self.specializzazione}) - {self.palestra.nome}"

class PrenotazioneContatto(models.Model):
    palestra = models.ForeignKey(Palestra, on_delete=models.CASCADE, related_name='prenotazioni')
    nome_utente = models.CharField(max_length=100)
    email = models.EmailField()
    telefono = models.CharField(max_length=20)
    messaggio = models.TextField()
    data_richiesta = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Richiesta da {self.nome_utente} per {self.palestra.nome}"

class Course(models.Model):
    # Supporto multi-tenant (collegato alla palestra di competenza)
    gym = models.ForeignKey('gym.Palestra', on_delete=models.CASCADE, related_name='courses')
    name = models.CharField(max_length=100) # Es. Spinning, CrossFit
    description = models.TextField(blank=True)
    max_capacity = models.PositiveIntegerField(default=20) # Posti massimi

    def __str__(self):
        return f"{self.name} ({self.gym.name})"


class CourseSession(models.SessionManager if hasattr(models, 'SessionManager') else models.Model): # Sessione specifica in calendario
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sessions')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    def __str__(self):
        return f"{self.course.name} - {self.start_time.strftime('%d/%m/%Y %H:%M')}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ('confirmed', 'Confermata'),
        ('waitlist', 'In Lista d\'Attesa'),
        ('cancelled', 'Cancellata'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session = models.ForeignKey(CourseSession, on_delete=models.CASCADE, related_name='bookings')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'session') # Un utente può avere una sola prenotazione per sessione

    def __str__(self):
        return f"{self.user.email} -> {self.session} [{self.status}]"


class SubscriptionPlan(models.Model):
    gym = models.ForeignKey('gym.Palestra', on_delete=models.CASCADE, related_name='subscription_plans')
    name = models.CharField(max_length=100) # Es. Mensile Open
    duration_days = models.PositiveIntegerField(default=30) # Durata in giorni
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.name} - {self.gym.nome} (€{self.price})"


class UserSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Calcola automaticamente la scadenza se non impostata, basandosi sui giorni del piano
        if not self.end_date and self.plan:
            self.end_date = self.start_date + timezone.timedelta(days=self.plan.duration_days)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Restituisce True se la data odierna ha superato la scadenza"""
        return timezone.now().date() > self.end_date

    @property
    def days_left(self):
        if self.end_date:
            delta = self.end_date - timezone.now().date()
            return max(delta.days, 0)
        return 0

    def __str__(self):
        status = "Scaduto" if self.is_expired else "Attivo"
        return f"{self.user.email} -> {self.plan.name} [{status}]"


class WorkoutPlan(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workout_plans')
    title = models.CharField(max_length=200)  # Es. "Scheda Ipertrofia - Giorno A"
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} ({self.user.username})"

class WorkoutExercise(models.Model):
    workout_plan = models.ForeignKey(WorkoutPlan, on_delete=models.CASCADE, related_name='exercises')
    name = models.CharField(max_length=150)  # Es. "Panca Piana con Bilanciere"
    sets = models.PositiveIntegerField(default=3)  # Numero di serie
    reps = models.CharField(max_length=50)  # Ripetizioni (es. "10-12" o "15")
    # Aggiungi questo campo nel modello degli esercizi della scheda
    rest_time = models.CharField(max_length=20, blank=True, null=True, verbose_name="Tempo di Recupero")
    weight = models.CharField(max_length=50, blank=True, null=True)  # Carico consigliato (es. "70 kg")
    notes = models.TextField(blank=True, null=True)  # Note tecniche sull'esecuzione
    # Aggiungi questo campo nel modello WorkoutExercise
    video_file = models.FileField(upload_to='exercises_videos/', blank=True, null=True, verbose_name="File Video Esercizio")
    # 3. La proprietà Python per convertire il link normale in un player incorporato pulito
    @property
    def video_embed_url(self):
        if self.video_url:
            if "watch?v=" in self.video_url:
                video_id = self.video_url.split("watch?v=")[-1].split("&")[0]
                return f"https://www.youtube.com/embed/{video_id}?rel=0"
            elif "youtu.be/" in self.video_url:
                video_id = self.video_url.split("youtu.be/")[-1].split("?")[0]
                return f"https://www.youtube.com/embed/{video_id}?rel=0"
        return self.video_url

    def __str__(self):
        return f"{self.name} - {self.sets}x{self.reps} [{self.workout_plan.title}]"

class CourseBooking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(CorsoOnline, on_delete=models.CASCADE) # Assicurati che punti a CorsoOnline
    booking_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='Confermato')

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user.username} - {self.course.title}"

class UserProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='progress_records')
    date = models.DateField(default=timezone.now)
    weight = models.DecimalField(max_digits=5, decimal_places=2, help_text="Peso in kg")
    body_fat = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, help_text="% Massa Grassa")
    muscle_mass = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, help_text="% Massa Magra")
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.date} ({self.weight} kg)"


class ExerciseLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exercise_logs')
    exercise = models.ForeignKey(WorkoutExercise, on_delete=models.CASCADE, related_name='logs')
    actual_weight = models.CharField(max_length=50, blank=True, null=True, verbose_name="Carico Effettivo Usato")
    feedback = models.TextField(blank=True, null=True, verbose_name="Nota/Feedback per il Trainer")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'exercise') # Un solo log per esercizio per utente

    def __str__(self):
        return f"{self.user.username} - {self.exercise.name} [{self.actual_weight}]"


class DietPlan(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='diet_plans')
    title = models.CharField(max_length=200, verbose_name="Titolo Piano Alimentare")
    description = models.TextField(blank=True, null=True, verbose_name="Linee Guida / Consigli Nutrizionali")
    pdf_file = models.FileField(upload_to='diet_pdfs/', blank=True, null=True, verbose_name="File PDF Dieta")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, verbose_name="Attiva")

    def __str__(self):
        return f"Dieta: {self.title} - {self.user.username}"


class CheckIn(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='checkins')
    timestamp = models.DateTimeField(auto_now_add=True)
    is_valid = models.BooleanField(default=True, verbose_name="Abbonamento Valido")
    notes = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        status = "VALIDO" if self.is_valid else "SCADUTO/NEGATO"
        return f"Check-in: {self.user.username} ({self.timestamp.strftime('%d/%m/%Y %H:%M')}) - {status}"


class ChatMessage(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_messages')
    message = models.TextField(verbose_name="Testo Messaggio")
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Da {self.sender.username} a {self.receiver.username}: {self.message[:30]}"

class UserBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='badges')
    title = models.CharField(max_length=100, verbose_name="Titolo Badge")
    description = models.TextField(verbose_name="Descrizione Obiettivo")
    icon_emoji = models.CharField(max_length=10, default="🏆", verbose_name="Emoji Icona")
    date_earned = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150, verbose_name="Titolo")
    message = models.TextField(verbose_name="Messaggio")
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notifica per {self.user.username}: {self.title}"

class ProgressPhoto(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='progress_photos')
    image = models.ImageField(upload_to='progress_photos/', verbose_name="Foto Progresso")
    caption = models.CharField(max_length=200, blank=True, null=True, verbose_name="Didascalia o Note")
    date = models.DateField(auto_now_add=True, verbose_name="Data Caricamento")

    def __str__(self):
        return f"Foto di {self.user.username} - {self.date}"


class ReferralProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referral_profile')
    code = models.CharField(max_length=20, unique=True, verbose_name="Codice Invito")
    referred_count = models.IntegerField(default=0, verbose_name="Amici Invitati")

    def __str__(self):
        return f"Referral {self.user.username} - {self.code}"


class VideoLesson(models.Model):
    title = models.CharField(max_length=150, verbose_name="Titolo Lezione")
    description = models.TextField(verbose_name="Descrizione")
    video_file = models.FileField(upload_to='videos/', verbose_name="File Video (MP4)", blank=True, null=True)
    duration = models.CharField(max_length=20, verbose_name="Durata (es. 45 min)")
    instructor = models.CharField(max_length=100, verbose_name="Istruttore")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.instructor})"

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=100, verbose_name="Titolo")
    message = models.TextField(verbose_name="Messaggio")
    is_read = models.BooleanField(default=False, verbose_name="Letta")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notifica per {self.user.username} - {self.title}"


class SmsWhatsappLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sms_whatsapp_logs')
    phone_number = models.CharField(max_length=20, verbose_name="Numero di Telefono")
    channel = models.CharField(max_length=10, choices=[('WHATSAPP', 'WhatsApp'), ('SMS', 'SMS')], default='WHATSAPP', verbose_name="Canale")
    message_type = models.CharField(max_length=50, verbose_name="Tipo Avviso (es. Scadenza, Promemoria)")
    message_body = models.TextField(verbose_name="Testo Messaggio")
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='Inviato', verbose_name="Stato")

    def __str__(self):
        return f"[{self.channel}] {self.user.username} - {self.message_type}"




class MemberPass(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='member_pass')
    pass_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_active = models.BooleanField(default=True, verbose_name="Pass Attivo")
    issued_at = models.DateTimeField(auto_now_add=True)
    serial_number = models.CharField(max_length=100, unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.serial_number:
            self.serial_number = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Pass Digitale - {self.user.username}"


class GymLiveStatus(models.Model):
    occupancy_percentage = models.IntegerField(default=45, verbose_name="Affluenza Attuale (%)")
    status_label = models.CharField(max_length=50, default="Tranquillo & Ottimale", verbose_name="Stato Affluenza")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Affluenza Palestra: {self.occupancy_percentage}% ({self.status_label})"


class GymEquipment(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nome Attrezzo")
    category = models.CharField(max_length=50, verbose_name="Categoria (es. Cardio, Isotonico, Sala Pesi)")
    status = models.CharField(
        max_length=20, 
        choices=[
            ('OTTIMO', '🟢 Operativo / Perfetto'), 
            ('MANUTENZIONE', '🟠 In Manutenzione Programmata'), 
            ('GUASTO', '🔴 Fuori Uso / Segnalato')
        ], 
        default='OTTIMO',
        verbose_name="Stato Attrezzo"
    )
    last_check_date = models.DateField(auto_now_add=True, verbose_name="Ultimo Controllo")

    def __str__(self):
        return f"{self.name} ({self.status})"



class CheckInLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_exit = models.BooleanField(default=False)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    medical_certificate_expiry = models.DateField(blank=True, null=True)



class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    age = models.IntegerField(blank=True, null=True)
    height = models.FloatField(blank=True, null=True)
    weight = models.FloatField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    medical_certificate_expiry = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"Profilo di {self.user.username}"



class GymCourse(models.Model):
    title = models.CharField(max_length=100)
    instructor = models.CharField(max_length=100)
    schedule_time = models.DateTimeField()
    max_capacity = models.IntegerField(default=15)
    current_booked = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.title} con {self.instructor}"

    @property
    def available_spots(self):
        return self.max_capacity - self.current_booked

class Recensione(models.Model):
    palestra = models.ForeignKey(Palestra, on_delete=models.CASCADE, related_name='recensioni')
    utente = models.ForeignKey(User, on_delete=models.CASCADE)
    valutazione = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)], default=5)  # Da 1 a 5 stelle
    commento = models.TextField()
    data_creazione = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.utente.username} - {self.valutazione} stelle ({self.palestra.nome})"


def media_recensioni(self):
        recensioni = self.recensioni.all()
        if recensioni.exists():
            return round(sum(r.valutazione for r in recensioni) / recensioni.count(), 1)
        return 0.0


class SlotOrario(models.Model):
    corso = models.ForeignKey('CorsoOnline', on_delete=models.CASCADE, related_name='slot_orari')
    giorno_settimana = models.CharField(max_length=20, choices=[
        ('Lunedi', 'Lunedì'),
        ('Martedi', 'Martedì'),
        ('Mercoledi', 'Mercoledì'),
        ('Giovedi', 'Giovedì'),
        ('Venerdi', 'Venerdì'),
        ('Sabato', 'Sabato'),
        ('Domenica', 'Domenica'),
    ])
    ora_inizio = models.TimeField()
    ora_fine = models.TimeField()
    posti_disponibili = models.PositiveIntegerField(default=20)

    def __str__(self):
        return f"Slot Corso #{self.corso.id} - {self.giorno_settimana} ({self.ora_inizio} - {self.ora_fine})"

class PrenotazioneCorso(models.Model):
    utente = models.ForeignKey(User, on_delete=models.CASCADE)
    slot = models.ForeignKey(SlotOrario, on_delete=models.CASCADE, related_name='prenotazioni')
    data_prenotazione = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.utente.username} - {self.slot}"


