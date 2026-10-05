import io
import json
import zipfile
import base64
from io import BytesIO
import qrcode
import stripe

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from .models import SlotOrario, PrenotazioneCorso
from .models import Palestra, Recensione
from .models import CourseBooking
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as auth_login
from .models import (
    Palestra, Attrezzo, CorsoOnline, CategoriaAttrezzo, 
    Abbonamento, OrarioApertura, PersonalTrainer, 
    PrenotazioneContatto, UserSubscription, WorkoutPlan, WorkoutExercise,
    CourseBooking, UserProgress, ExerciseLog, DietPlan, CheckIn, ChatMessage, UserBadge, ProgressPhoto,
    ReferralProfile, VideoLesson, Notification, SmsWhatsappLog,
    MemberPass, GymLiveStatus, GymEquipment, CheckInLog, UserProfile, GymCourse,
    SubscriptionPlan, SlotOrario, UserSubscription
    
)
from .forms import UserProfileForm
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from .models import Palestra


stripe.api_key = settings.STRIPE_SECRET_KEY


# ==========================================
# 1. VISTE PUBBLICHE & CATALOGO
# ==========================================

def home_view(request):
    palestre = Palestra.objects.all()
    attrezzi = Attrezzo.objects.all()
    corsi = CorsoOnline.objects.all()
    abbonamenti = Abbonamento.objects.all()
    orari = OrarioApertura.objects.all()
    trainers = PersonalTrainer.objects.all()

    context = {
        'palestre': palestre,
        'attrezzi': attrezzi,
        'corsi': corsi,
        'abbonamenti': abbonamenti,
        'orari': orari,
        'trainers': trainers
    }
    return render(request, 'index.html', context)


def checkout(request, corso_id):
    corso = get_object_or_404(CorsoOnline, id=corso_id)
    context = {
        'corso': corso,
    }
    return render(request, 'checkout.html', context)


def palestra_detail(request, slug):
    palestra = get_object_or_404(Palestra, slug=slug)
    abbonamenti = Abbonamento.objects.filter(palestra=palestra)
    orari = OrarioApertura.objects.filter(palestra=palestra)
    trainers = PersonalTrainer.objects.filter(palestra=palestra)

    user_subscription = None
    if request.user.is_authenticated:
        user_subscription = UserSubscription.objects.filter(
            user=request.user, 
            plan__gym=palestra, 
            is_active=True
        ).order_by('-end_date').first()

    attrezzi = palestra.attrezzi.all()
    corsi = CorsoOnline.objects.all()


    if request.method == 'POST':
        nome = request.POST.get('nome')
        email = request.POST.get('email')
        telefono = request.POST.get('telefono')
        messaggio = request.POST.get('messaggio')
        
        PrenotazioneContatto.objects.create(
            palestra=palestra,
            nome_utente=nome,
            email=email,
            telefono=telefono,
            messaggio=messaggio
        )
        messages.success(request, 'La tua richiesta di contatto è stata inviata con successo!')
        return redirect('palestra_detail', slug=palestra.slug)
    
    context = {
        'palestra': palestra,
        'attrezzi': attrezzi,
        'corsi': corsi,
        'abbonamenti': abbonamenti,
        'orari': orari,
        'trainers': trainers,
        'subscription': user_subscription,
        'user_subscription': user_subscription,
    }
    return render(request, 'palestra_detail.html', context)


def esercizi_online(request):
    corsi = CorsoOnline.objects.all()
    return render(request, 'esercizi_online.html', {'corsi': corsi})


def area_attrezzi_main(request, slug):
    palestra = get_object_or_404(Palestra, slug=slug)
    categories = CategoriaAttrezzo.objects.all()
    attrezzi = palestra.attrezzi.all()
    orari = palestra.orari.all()
    
    categorie_ids = attrezzi.values_list('categoria_id', flat=True).distinct()
    categorie = CategoriaAttrezzo.objects.filter(id__in=categorie_ids)
    trainers = palestra.trainers.all()

    context = {
        'palestra': palestra,
        'categories': categories,
        'attrezzi': attrezzi,
        'trainers': trainers,
        'orari': orari,
        'categorie': categorie,
    }
    return render(request, 'area_attrezzi_main.html', context)


def categoria_detail(request, slug, categoria_id):
    palestra = get_object_or_404(Palestra, slug=slug)
    categoria = get_object_or_404(CategoriaAttrezzo, id=categoria_id)
    attrezzi = Attrezzo.objects.filter(palestra=palestra, categoria=categoria)
    
    context = {
        'palestra': palestra,
        'categoria': categoria,
        'attrezzi': attrezzi,
    }
    return render(request, 'categoria_detail.html', context)


# ==========================================
# 2. DASHBOARD UTENTE & WORKOUT
# ==========================================

@login_required
def profilo_utente_view(request):
    today = timezone.now().date()
    prenotazione_oggi = CourseBooking.objects.filter(user=request.user).order_by('-id').first()
    
    # 1. Recupero o creazione del profilo utente e del pass
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    member_pass, _ = MemberPass.objects.get_or_create(user=request.user)
    available_courses = CorsoOnline.objects.all()
    
    # 2. URL e generazione QR Code per l'accesso smart
    checkin_url = request.build_absolute_uri(f'/checkin/{member_pass.pass_code}/')
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(checkin_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()

        # All'interno della tua vista profilo
    # 2. Gestione della prenotazione corso via POST
    if request.method == 'POST' and 'book_course_id' in request.POST:
        course_id = request.POST.get('book_course_id')
        corso = get_object_or_404(CorsoOnline, id=course_id)
        
        # Verifichiamo i posti disponibili usando l'istanza corretta di CorsoOnline
        if corso.available_spots > 0:
            booking, created = CourseBooking.objects.get_or_create(user=request.user, course=corso)
            if created:
                corso.current_booked += 1
                corso.save()
                messages.success(request, f"Corso '{corso.title}' prenotato con successo!")
            else:
                messages.warning(request, "Hai già prenotato questo corso.")
        else:
            messages.error(request, "Spiacenti, il corso è al completo.")
        return redirect('profile')
        
    # 3. Gestione POST Form multipli nella dashboard
    if request.method == 'POST':
        # Aggiornamento Foto Profilo
        if 'photo' in request.FILES or 'upload_profile_photo' in request.POST:
            form = UserProfileForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, "Foto profilo aggiornata con successo!")
                return redirect('profilo_utente')


        # Aggiornamento Dati Anagrafici & Antropometrici del Profilo
        elif 'update_personal_data' in request.POST:
            request.user.first_name = request.POST.get('first_name', '').strip()
            request.user.last_name = request.POST.get('last_name', '').strip()
            request.user.save()

            profile.age = request.POST.get('age') or None
            profile.height = request.POST.get('height') or None
            profile.weight = request.POST.get('weight') or None
            profile.phone = request.POST.get('phone', '').strip()
            profile.save()

            messages.success(request, "Dati anagrafici e antropometrici salvati con successo!")
            return redirect('profilo_utente')

        # Generazione Piano AI
        elif 'generate_ai_plan' in request.POST:
            goal = request.POST.get('ai_goal', 'Massa Muscolare')
            level = request.POST.get('ai_level', 'Intermedio')
            
            w_plan = WorkoutPlan.objects.create(
                user=request.user,
                title=f"AI Smart Plan: {goal} ({level})",
                description=f"Programma generato automaticamente da TrudAI Engine basato su obiettivo {goal} e livello {level}."
            )
            
            if goal == 'Massa Muscolare':
                WorkoutExercise.objects.create(workout_plan=w_plan, name="Panca Piana Bilanciere", sets=4, reps="8-10", rest_time="90 sec")
                WorkoutExercise.objects.create(workout_plan=w_plan, name="Squat con Bilanciere", sets=4, reps="6-8", rest_time="120 sec")
                WorkoutExercise.objects.create(workout_plan=w_plan, name="Rematore con Manubrio", sets=3, reps="10", rest_time="60 sec")
            elif goal == 'Definizione / Cardio':
                WorkoutExercise.objects.create(workout_plan=w_plan, name="HIIT Tapis Roulant", sets=5, reps="3 min", rest_time="45 sec")
                WorkoutExercise.objects.create(workout_plan=w_plan, name="Burpees & Mountain Climbers", sets=4, reps="15 reps", rest_time="30 sec")
                WorkoutExercise.objects.create(workout_plan=w_plan, name="Addominali Crunch a Terra", sets=4, reps="20 reps", rest_time="30 sec")
            else:
                WorkoutExercise.objects.create(workout_plan=w_plan, name="Stacco da Terra", sets=5, reps="5 reps", rest_time="180 sec")
                WorkoutExercise.objects.create(workout_plan=w_plan, name="Lento Avanti Militare", sets=4, reps="8 reps", rest_time="90 sec")

            DietPlan.objects.create(
                user=request.user,
                title=f"Dieta Smart AI - {goal}",
                description="Colazione: Pancakes proteici.\nPranzo: Riso basmati con pollo.\nCena: Salmone e verdure."
            )
            messages.success(request, f"TrudAI Engine ha generato il tuo programma per '{goal}'!")
            return redirect('profilo_utente')

        # Segna notifiche come lette
        elif 'mark_notifications_read' in request.POST:
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
            messages.success(request, "Tutte le notifiche sono state segnate come lette.")
            return redirect('profilo_utente')

        # Salvataggio diario carichi esercizi
        elif 'save_exercise_log' in request.POST:
            exercise_id = request.POST.get('exercise_id')
            actual_weight = request.POST.get('actual_weight')
            feedback = request.POST.get('feedback')
            exercise = get_object_or_404(WorkoutExercise, id=exercise_id)
            
            ExerciseLog.objects.update_or_create(
                user=request.user,
                exercise=exercise,
                defaults={'actual_weight': actual_weight, 'feedback': feedback}
            )
            messages.success(request, f"Carico salvato per {exercise.name}!")
            return redirect('profilo_utente')

        # Upload foto progressi
        elif 'upload_progress_photo' in request.POST:
            photo_file = request.FILES.get('progress_image')
            caption = request.POST.get('caption', '').strip()
            if photo_file:
                ProgressPhoto.objects.create(user=request.user, image=photo_file, caption=caption)
                messages.success(request, "Foto dei progressi caricata con successo!")
                return redirect('profilo_utente')

        # Riscatto codice Referral
        elif 'redeem_referral_code' in request.POST:
            input_code = request.POST.get('referral_code', '').strip().upper()
            ref_profile, _ = ReferralProfile.objects.get_or_create(
                user=request.user,
                defaults={'code': f"TRUD{request.user.id}GYM{request.user.username[:3].upper()}"}
            )
            if input_code == ref_profile.code:
                messages.error(request, "Non puoi utilizzare il tuo stesso codice invito!")
            else:
                try:
                    inviter_profile = ReferralProfile.objects.get(code=input_code)
                    inviter_profile.referred_count += 1
                    inviter_profile.save()
                    messages.success(request, f"Codice di {inviter_profile.user.username} applicato! 7 giorni extra sbloccati.")
                except ReferralProfile.DoesNotExist:
                    messages.error(request, "Codice invito non valido o inesistente.")
            return redirect('profilo_utente')
    

    # Gestione ritorno da Stripe
    if request.GET.get('pagamento') == 'successo':
        sub = UserSubscription.objects.filter(user=request.user).order_by('-end_date').first()
        


        if sub:
            if sub.end_date < today:
                sub.start_date = today
                sub.end_date = today + timezone.timedelta(days=30)
            else:
                sub.end_date += timezone.timedelta(days=30)
            sub.save()

        send_mail(
            subject='Conferma Rinnovo Abbonamento - Trud Gyms',
            message=f'Ciao {request.user.username},\n\nIl tuo abbonamento è stato rinnovato con successo per altri 30 giorni.',
            from_email='noreply@trudgyms.local',
            recipient_list=[request.user.email or "utente@trudgyms.local"],
            fail_silently=True,
        )
        messages.success(request, "Pagamento completato! Abbonamento rinnovato di 30 giorni.")
        return redirect('profilo_utente')

    elif request.GET.get('pagamento') == 'annullato':
        messages.warning(request, "Il processo di pagamento è stato annullato.")
        return redirect('profilo_utente')

    # Query di contesto per il template profilo.html
    form = UserProfileForm(instance=profile)
    video_lessons = VideoLesson.objects.all().order_by('-created_at')
    gym_status, _ = GymLiveStatus.objects.get_or_create(id=1)
    equipment_list = GymEquipment.objects.all()
    sms_whatsapp_logs = SmsWhatsappLog.objects.filter(user=request.user).order_by('-sent_at')
    
    latest_progress = UserProgress.objects.filter(user=request.user).order_by('-date').first()
    estimated_calories = int(float(latest_progress.weight) * 33) if latest_progress and latest_progress.weight else 2450
    estimated_protein = int(float(latest_progress.weight) * 2.2) if latest_progress and latest_progress.weight else 160

    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:5]
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()

    if not UserBadge.objects.filter(user=request.user).exists():
        UserBadge.objects.create(
            user=request.user,
            title="Pioniere TrudGyms",
            description="Hai attivato con successo il tuo account sulla piattaforma enterprise!",
            icon_emoji="🚀"
        )
    user_badges = UserBadge.objects.filter(user=request.user).order_by('-date_earned')

    referral_profile, _ = ReferralProfile.objects.get_or_create(
        user=request.user,
        defaults={'code': f"TRUD{request.user.id}GYM{request.user.username[:3].upper()}"}
    )
    if not referral_profile.code:
        referral_profile.code = f"TRUD{request.user.id}GYM{request.user.username[:3].upper()}"
        referral_profile.save()

    user_subscription = UserSubscription.objects.filter(user=request.user).order_by('-end_date').first()
    workout_plans = WorkoutPlan.objects.filter(user=request.user, is_active=True)
    diet_plans = DietPlan.objects.filter(user=request.user, is_active=True)
    course_bookings = CourseBooking.objects.filter(user=request.user).order_by('-booking_date')
    progress_records = UserProgress.objects.filter(user=request.user).order_by('-date')
    exercise_logs = {log.exercise_id: log for log in ExerciseLog.objects.filter(user=request.user)}

    context = {
        'form': form,
        'profile': profile,
        'subscription': user_subscription,
        'user_subscription': user_subscription,
        'workout_plans': workout_plans,
        'diet_plans': diet_plans,
        'course_bookings': course_bookings,
        'progress_records': progress_records,
        'exercise_logs': exercise_logs,
        'user_badges': user_badges,
        'estimated_calories': estimated_calories,
        'estimated_protein': estimated_protein,
        'progress_photos': ProgressPhoto.objects.filter(user=request.user).order_by('-date'),
        'referral_profile': referral_profile,
        'video_lessons': video_lessons,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'sms_whatsapp_logs': sms_whatsapp_logs,
        'member_pass': member_pass,
        'user_pass': member_pass,
        'gym_status': gym_status,
        'equipment_list': equipment_list,
        'qr_code_base64': qr_code_base64,
        'available_courses': available_courses,
        'prenotazione_oggi': prenotazione_oggi,
    }
    return render(request, 'profilo.html', context)


@login_required
def prenota_corso(request, corso_id):
    corso = get_object_or_404(CorsoOnline, id=corso_id)
    prenotazioni_attuali = CourseBooking.objects.filter(course=corso).count()
    max_limite = getattr(corso, 'max_posti', 15)
    
    if prenotazioni_attuali >= max_limite:
        messages.error(request, "Spiacenti, questo corso ha raggiunto il numero massimo di partecipanti!")
        return redirect('palestra_detail', slug=corso.palestra.slug)
    
    existing_booking = CourseBooking.objects.filter(user=request.user, course=corso).first()
    if not existing_booking:
        CourseBooking.objects.create(user=request.user, course=corso, status='Confermato')
        messages.success(request, f"Corso '{corso.titolo}' prenotato con successo!")
    else:
        messages.warning(request, f"Hai già prenotato il corso '{corso.titolo}' in precedenza.")
        
    return redirect('profilo_utente')


# ==========================================
# 3. GESTIONE TENANT, STRIPE & RECEPTION
# ==========================================

@login_required
def tenant_dashboard_view(request):
    if not request.user.is_staff:
        messages.error(request, "Accesso non autorizzato. Sezione riservata ai gestori.")
        return redirect('profilo_utente')

    palestra = Palestra.objects.first()
    today = timezone.now().date()

    if request.method == 'POST' and 'crea_slot' in request.POST:
        corso_id = request.POST.get('corso')
        giorno = request.POST.get('giorno_settimana')
        ora_inizio = request.POST.get('ora_inizio')
        ora_fine = request.POST.get('ora_fine')
        posti = request.POST.get('posti_disponibili', 20)

        if corso_id and giorno and ora_inizio and ora_fine:
            corso = CorsoOnline.objects.get(id=corso_id)
            SlotOrario.objects.create(
                corso=corso,
                giorno_settimana=giorno,
                ora_inizio=ora_inizio,
                ora_fine=ora_fine,
                posti_disponibili=posti
            )
            return redirect('tenant_dashboard')
        
    active_subscriptions_count = UserSubscription.objects.filter(end_date__gte=today).count()
    expiring_soon_count = UserSubscription.objects.filter(
        end_date__gte=today, 
        end_date__lte=today + timezone.timedelta(days=7)
    ).count()
    recent_bookings = CourseBooking.objects.order_by('-booking_date')[:5]
    corsi = CorsoOnline.objects.all()
    slot_orari = SlotOrario.objects.select_related('corso').all()
    
    context = {
        'palestra': palestra,
        'active_subscriptions_count': active_subscriptions_count,
        'expiring_soon_count': expiring_soon_count,
        'recent_bookings': recent_bookings,
        'corsi': corsi,
        'slot_orari': slot_orari,
    }
    return render(request, 'tenant_dashboard.html', context)


@login_required
def crea_checkout_stripe(request):
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {'name': 'Abbonamento Mensile - Trud Gyms'},
                    'unit_amount': 4900,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=request.build_absolute_uri(reverse('profilo_utente')) + '?pagamento=successo',
            cancel_url=request.build_absolute_uri(reverse('profilo_utente')) + '?pagamento=annullato',
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        messages.error(request, f"Errore durante la creazione del pagamento: {str(e)}")
        return redirect('profilo_utente')


@login_required
def receptionist_checkin_view(request):
    if not request.user.is_staff:
        messages.error(request, "Accesso negato. Area riservata allo staff.")
        return redirect('profilo_utente')

    result_message = None
    is_success = False

    if request.method == 'POST':
        qr_code_data = request.POST.get('qr_data', '').strip()
        if 'TRUD-GYMS-ACCESS-' in qr_code_data or len(qr_code_data) > 0:
            # Estrazione pass code o username
            try:
                member_pass = MemberPass.objects.filter(Q(pass_code=qr_code_data) | Q(user__username=qr_code_data)).first()
                if member_pass:
                    sub = UserSubscription.objects.filter(user=member_pass.user).order_by('-end_date').first()
                    if sub and not sub.is_expired:
                        CheckIn.objects.create(user=member_pass.user, is_valid=True, notes="Accesso consentito")
                        result_message = f"✅ Accesso consentito per {member_pass.user.username}!"
                        is_success = True
                    else:
                        CheckIn.objects.create(user=member_pass.user, is_valid=False, notes="Abbonamento scaduto")
                        result_message = f"❌ Abbonamento scaduto per {member_pass.user.username}!"
                else:
                    result_message = "⚠️ Pass non trovato nel sistema."
            except Exception as e:
                result_message = f"⚠️ Errore di verifica: {str(e)}"

    recent_checkins = CheckIn.objects.all().order_by('-timestamp')[:10]
    context = {
        'result_message': result_message,
        'is_success': is_success,
        'recent_checkins': recent_checkins,
    }
    return render(request, 'checkin_reception.html', context)


# ==========================================
# 4. CHAT, PWA & LEADERBOARD
# ==========================================

@login_required
def chat_view(request):
    User = get_user_model()
    if request.user.is_staff:
        contact_id = request.GET.get('user_id')
        selected_user = get_object_or_404(User, id=contact_id) if contact_id else User.objects.filter(is_staff=False).first()
        contacts = User.objects.filter(is_staff=False)
    else:
        selected_user = User.objects.filter(is_staff=True).first()
        contacts = User.objects.filter(is_staff=True)

    if not selected_user:
        messages.warning(request, "Nessun contatto disponibile per la chat al momento.")
        return redirect('profilo_utente')

    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        if message_text:
            ChatMessage.objects.create(sender=request.user, receiver=selected_user, message=message_text)
            redirect_url = f"{request.path}?user_id={selected_user.id}" if request.user.is_staff else request.path
            return redirect(redirect_url)

    chat_messages = ChatMessage.objects.filter(
        (Q(sender=request.user) & Q(receiver=selected_user)) |
        (Q(sender=selected_user) & Q(receiver=request.user))
    ).order_by('timestamp')

    context = {
        'selected_user': selected_user,
        'chat_messages': chat_messages,
        'contacts': contacts,
    }
    return render(request, 'chat.html', context)


def manifest_view(request):
    data = {
        "name": "Trud Gyms Platform",
        "short_name": "TrudGyms",
        "start_url": "/profilo/",
        "display": "standalone",
        "background_color": "#030712",
        "theme_color": "#f97316",
        "icons": [
            {"src": "https://api.qrserver.com/v1/create-qr-code/?size=192x192&data=TRUD-GYMS", "sizes": "192x192", "type": "image/png"},
            {"src": "https://api.qrserver.com/v1/create-qr-code/?size=512x512&data=TRUD-GYMS", "sizes": "512x512", "type": "image/png"}
        ]
    }
    return JsonResponse(data)


def serviceworker_view(request):
    js_code = """
    self.addEventListener('install', (e) => { console.log('TrudGyms Service Worker installed'); });
    self.addEventListener('fetch', (e) => { e.respondWith(fetch(e.request).catch(() => caches.match(e.request))); });
    """
    return HttpResponse(js_code, content_type="application/javascript")


@login_required
def leaderboard_view(request):
    User = get_user_model()
    users_ranking = User.objects.annotate(
        badges_count=Count('badges'),
        checkins_count=Count('checkins')
    ).order_by('-badges_count', '-checkins_count')[:10]

    context = {'users_ranking': users_ranking}
    return render(request, 'leaderboard.html', context)


def checkin_view(request, pass_code):
    member_pass = get_object_or_404(MemberPass, pass_code=pass_code)
    is_valid = True
    error_reason = ""

    if not member_pass.is_active:
        is_valid = False
        error_reason = "Abbonamento scaduto o non attivo"

    status_color = "#10B981" if is_valid else "#EF4444"
    status_text = "ACCESSO CONSENTITO" if is_valid else "ACCESSO NEGATO"
    sub_text = f"Benvenuto, {member_pass.user.get_full_name() or member_pass.user.username}" if is_valid else error_reason
    speech_message = f"Benvenuto {member_pass.user.first_name or member_pass.user.username}" if is_valid else f"Accesso negato. {error_reason}"

    avatar_content = f"{member_pass.user.username[:1].upper()}"
    if hasattr(member_pass.user, 'userprofile') and member_pass.user.userprofile.photo:
        avatar_content = f'<img src="{member_pass.user.userprofile.photo.url}" alt="Foto Profilo" style="width: 100%; height: 100%; object-fit: cover;">'

    return HttpResponse(f"""
    <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ background-color: #030712; color: white; font-family: sans-serif; text-align: center; padding-top: 50px; }}
                .card {{ background: #111827; border-radius: 16px; padding: 40px; max-width: 400px; margin: auto; border: 2px solid {status_color}; }}
                h1 {{ color: {status_color}; font-size: 28px; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div style="width: 100px; height: 100px; border-radius: 50%; overflow: hidden; display: flex; align-items: center; justify-content: center; background: #374151; margin: 0 auto 20px auto;">
                    {avatar_content}
                </div>
                <h1>{status_text}</h1>
                <p><strong>{sub_text}</strong></p>
            </div>
            <script>
                if ('speechSynthesis' in window) {{
                    var utterance = new SpeechSynthesisUtterance("{speech_message}");
                    utterance.lang = 'it-IT';
                    window.speechSynthesis.speak(utterance);
                }}
            </script>
        </body>
    </html>
    """)


def reception_live_view(request):
    return render(request, 'reception_live.html')


def api_checkin_verify(request, pass_code):
    try:
        member_pass = MemberPass.objects.get(pass_code=pass_code)
        return JsonResponse({"success": True, "user_name": member_pass.user.username, "is_active": member_pass.is_active})
    except MemberPass.DoesNotExist:
        return JsonResponse({"success": False, "error": "Pass non trovato"}, status=404)


def download_apple_pass(request, pass_code):
    member_pass = get_object_or_404(MemberPass, pass_code=pass_code)
    pass_data = {
        "formatVersion": 1,
        "passTypeIdentifier": "pass.com.gymsaas.platform",
        "serialNumber": member_pass.serial_number,
        "teamIdentifier": "YOUR_TEAM_ID",
        "organizationName": "Gym SaaS Platform",
        "description": "Tessera Palestra",
        "logoText": "Palestra Member",
        "foregroundColor": "rgb(255, 255, 255)",
        "backgroundColor": "rgb(3, 7, 18)",
        "barcode": {"message": str(member_pass.pass_code), "format": "PKBarcodeFormatQR", "messageEncoding": "iso-8859-1"},
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr('pass.json', json.dumps(pass_data, indent=4))
    buffer.seek(0)
    
    response = HttpResponse(buffer.read(), content_type='application/vnd.apple.pkpass')
    response['Content-Disposition'] = f'attachment; filename=gym_pass_{member_pass.serial_number}.pkpass'
    return response


def google_wallet_pass__view(request, pass_code):
    member_pass = get_object_or_404(MemberPass, pass_code=pass_code)
    save_url = "https://pay.google.com/gp/v/save"
    return HttpResponse(f"""
    <html>
        <head><meta charset="utf-8"><title>Google Wallet</title></head>
        <body style="background: #030712; color: white; text-align: center; padding-top: 50px;">
            <div style="background: #111827; padding: 40px; max-width: 400px; margin: auto; border-radius: 16px;">
                <h1>Google Wallet</h1>
                <p>Socio: <strong>{member_pass.user.username}</strong></p>
                <a href="{save_url}" style="background: white; color: black; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold;">Salva su Google Wallet</a>
            </div>
        </body>
    </html>
    """)


def get_live_count(request):
    count = CheckInLog.objects.filter(is_exit=False).count()
    return JsonResponse({'count': count})


def registrazione_view(request):
    if request.method == 'POST':
        # Qui gestiamo la creazione dell'utente e del profilo
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        
        # Dati antropometrici e profilo
        age = request.POST.get('age')
        height = request.POST.get('height')
        weight = request.POST.get('weight')
        phone = request.POST.get('phone')
        photo = request.FILES.get('photo')

        from django.contrib.auth.models import User
        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(username=username, password=password, first_name=first_name, last_name=last_name)
            
            # Recupera o crea il profilo
            profile, created = UserProfile.objects.get_or_create(user=user)
            if age: profile.age = age
            if height: profile.height = height
            if weight: profile.weight = weight
            if phone: profile.phone = phone
            if photo: profile.photo = photo
            profile.save()

            # Effettua il login automatico e reindirizza al profilo
            login(request, user)
            return redirect('profile')
            
    return render(request, 'registrazione.html')


def create_checkout_session(request, plan_id):
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    
    # URL di successo e fallimento
    # Sostituisci 'payment_success' con 'profile' (o la pagina che preferisci)
    success_url = request.build_absolute_uri(reverse('profile')) + '?session_id={CHECKOUT_SESSION_ID}'
    cancel_url = request.build_absolute_uri(reverse('profile'))

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': plan.name,
                    },
                    'unit_amount': int(plan.price * 100), # Stripe vuole i centesimi (es. 50.00 € = 5000)
                },
                'quantity': 1,
            }],
            mode='payment', # Oppure 'subscription' per abbonamenti ricorrenti
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=str(request.user.id),
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        return JsonResponse({'error': str(e)})


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=400)

    # Gestiamo l'evento di completamento del checkout
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.client_reference_id
        
        if user_id:
            user = User.objects.get(id=user_id)
            # Aggiorniamo o creiamo l'abbonamento attivo per l'utente nel database
            user_sub, created = UserSubscription.objects.get_or_create(user=user)
            user_sub.is_active = True
            user_sub.save()

    return HttpResponse(status=200)



def palestre_vetrina_view(request):
    palestre = Palestra.objects.all()
    citta_query = request.GET.get('citta', '')
    if citta_query:
        palestre = Palestra.objects.filter(citta__icontains=citta_query)
    else:
        palestre = Palestra.objects.all()
        
    # Recuperiamo anche l'elenco delle città uniche per i pulsanti di filtro rapido
    citta_disponibili = Palestra.objects.values_list('citta', flat=True).distinct()

    context = {
        'palestre': palestre,
        'citta_disponibili': citta_disponibili,
        'citta_selezionata': citta_query,
    }
    return render(request, 'vetrina.html', context)


@login_required
def prenota_slot_view(request, slot_id):
    slot = get_object_or_404(SlotOrario, id=slot_id)
    
    # Controlliamo se ci sono posti disponibili e se l'utente non ha già prenotato lo stesso slot
    già_prenotato = PrenotazioneCorso.objects.filter(utente=request.user, slot=slot).exists()
    
    if not già_prenotato and slot.posti_disponibili > 0:
        PrenotazioneCorso.objects.create(utente=request.user, slot=slot)
        slot.posti_disponibili -= 1
        slot.save()
        
    return redirect(request.META.get('HTTP_REFERER', 'vetrina_palestre'))



@login_required
def aggiungi_recensione(request, palestra_id):
    palestra = get_object_or_404(Palestra, id=palestra_id)
    
    if request.method == 'POST':
        valutazione = request.POST.get('valutazione')
        commento = request.POST.get('commento')
        
        if valutazione:
            # Controlla se l'utente ha già recensito questa palestra (opzionale, aggiorna o crea)
            Recensione.objects.update_or_create(
                palestra=palestra,
                utente=request.user,
                defaults={'valutazione': int(valutazione), 'commento': commento}
            )
            
    return redirect(request.META.get('HTTP_REFERER', 'vetrina_palestre'))



@login_required
def mio_abbonamento_view(request):
    # Recuperiamo l'abbonamento attivo dell'utente loggato
    abbonamento = UserSubscription.objects.filter(user=request.user).order_by('-end_date').first()
    
    qr_code_base64 = None
    if abbonamento:
        # Stringa univoca da inserire nel QR code (es. ID abbonamento e username)
        qr_data = f"GYM-PASS-{abbonamento.id}-{request.user.username}"
        
        # Generiamo il QR code in memoria con qrcode
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertiamo l'immagine in base64 per mostrarla direttamente nell'HTML
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    context = {
        'abbonamento': abbonamento,
        'qr_code_base64': qr_code_base64,
    }
    return render(request, 'mio_abbonamento.html', context)


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect('profile') # O alla dashboard della palestra
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def home_view(request):
    return render(request, 'home.html')