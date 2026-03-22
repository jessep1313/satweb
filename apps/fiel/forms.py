from django import forms
from .models import CargaFiel

class CargaFielForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=True, label='Contraseña')

    class Meta:
        model = CargaFiel
        fields = ['archivo_cer', 'archivo_key', 'password']
        widgets = {
            'archivo_cer': forms.FileInput(attrs={'accept': '.cer'}),
            'archivo_key': forms.FileInput(attrs={'accept': '.key'}),
        }