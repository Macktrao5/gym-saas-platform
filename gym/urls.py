from django.urls import path
from . import views 
from .views import profilo_utente_view
from .views import prenota_corso, tenant_dashboard_view, crea_checkout_stripe # <-- Assicurati di includere crea_checkout_stripe
from gym.views import checkin_view
from gym.views import reception_live_view, api_checkin_verify, download_apple_pass, google_wallet_pass__view


urlpatterns = [
    # Mettiamo 'index' come nome della rotta principale
    path('', views.home_view, name='index'),
    path('palestra/<slug:slug>/', views.palestra_detail, name='palestra_detail'),
    path('esercizi_online/', views.esercizi_online, name='exercises_online'),
    path('palestra/<slug:slug>/attrezzi/', views.area_attrezzi_main, name='area_attrezzi_main'),
    path('palestra/<slug:slug>/<int:categoria_id>/', views.categoria_detail, name='categoria_detail'),
    path('profilo/', views.profilo_utente_view, name='profilo_utente'),
    path('prenota-corso/<int:corso_id>/', views.prenota_corso, name='prenota_corso'),
    path('dashboard/', views.tenant_dashboard_view, name='tenant_dashboard'),
    path('crea-checkout-stripe/', crea_checkout_stripe, name='crea_checkout_stripe'),
    path('receptionist-checkin/', views.receptionist_checkin_view, name='receptionist_checkin'),
    path('chat/', views.chat_view, name='chat'),
    path('manifest.json', views.manifest_view, name='manifest'),
    path('sw.js', views.serviceworker_view, name='serviceworker'),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('checkin/<str:pass_code>/', checkin_view, name='checkin_view'),
    path('reception/', reception_live_view, name='reception_live_view'),
    path('api/checkin/<str:pass_code>/', api_checkin_verify, name='api_checkin_verify'),
    path('wallet/apple/<str:pass_code>/', download_apple_pass, name='download_apple_pass'),
    path('wallet/google/<str:pass_code>/', google_wallet_pass__view, name='download_google_pass'),
    path('api/live-count/', views.get_live_count, name='live_count'),
    path('profilo/', views.profilo_utente_view, name='profile'),
    path('registrazione/', views.registrazione_view, name='registrazione'),
    path('create-checkout-session/', views.crea_checkout_stripe, name='crea_checkout_stripe'),
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
    path('vetrina/', views.palestre_vetrina_view, name='vetrina_palestre'),
    path('prenota-slot/<int:slot_id>/', views.prenota_slot_view, name='prenota_slot'),
    path('palestra/<int:palestra_id>/recensisci/', views.aggiungi_recensione, name='aggiungi_recensione'),
    path('login/', views.login_view, name='login'),
    path('', views.home_view, name='home'),
    
    
]