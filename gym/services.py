from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Booking, UserSubscription

def book_course_session(user, session):
    with transaction.atomic():
        valid_subscription = UserSubscription.objects.filter(
            user=user,
            plan__gym=session.course.gym,
            is_active=True
        ).order_by('-end_date').first()

        if not valid_subscription or valid_subscription.is_expired:
            raise ValidationError("Non hai un abbonamento attivo o valido per questa palestra.")
        # ----------------------------------
        # Conta quanti posti confermati ci sono già per questa sessione
        confirmed_count = Booking.objects.filter(session=session, status='confirmed').count()
        max_limit = session.course.max_capacity

        # Verifica se l'utente ha già una prenotazione attiva
        existing_booking = Booking.objects.filter(user=user, session=session).first()
        if existing_booking and existing_booking.status != 'cancelled':
            raise ValidationError("Hai già una prenotazione attiva per questa sessione.")

        # Determina lo stato in base alla capienza
        if confirmed_count < max_limit:
            status = 'confirmed'
        else:
            status = 'waitlist' # Posti esauriti, va in coda!

        # Crea o aggiorna la prenotazione
        booking, created = Booking.objects.update_or_create(
            user=user,
            session=session,
            defaults={'status': status}
        )
        return booking

def cancel_booking(booking):
    with transaction.atomic():
        session = booking.session
        was_confirmed = (booking.status == 'confirmed')
        
        booking.status = 'cancelled'
        booking.save()

        # Se il posto era confermato, liberiamo uno slot per chi è in lista d'attesa
        if was_confirmed:
            first_in_waitlist = Booking.objects.filter(
                session=session, 
                status='waitlist'
            ).order_by('created_at').first()

            if first_in_waitlist:
                first_in_waitlist.status = 'confirmed'
                first_in_waitlist.save()