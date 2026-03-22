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

from django import forms
from .models import ConfiguracionCorreo

class ConfiguracionCorreoForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionCorreo
        fields = ['tipo', 'titulo', 'cuerpo']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'cuerpo': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
        }
        labels = {
            'tipo': 'Tipo',
            'titulo': 'Título',
            'cuerpo': 'Cuerpo',
        }