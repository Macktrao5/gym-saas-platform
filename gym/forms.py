from django import forms
from .models import UserProfile

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['photo'] # Aggiungi altri campi se desideri (es. telefono, ecc.)