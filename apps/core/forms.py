from django import forms
from django.contrib.auth.forms import AuthenticationForm


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Usuario'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}),
        required=True
    )
    empresa = forms.ChoiceField(
        choices=[
            ('', '—— Selecciona empresa ——'),
            ('empresa1', 'Empresa 1'),
            ('empresa2', 'Empresa 2'),
            ('empresa3', 'Empresa 3'),
            ('empresa4', 'Empresa 4'),
            ('empresa5', 'Empresa 5'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )


from usuarios_tenant.models import Usuario

class AdminCreationForm(forms.Form):
    nombre = forms.CharField(
        max_length=255,
        label='Nombre completo',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    usuario = forms.CharField(
        max_length=150,
        label='Usuario (login)',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Contraseña'
    )
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    empresa = forms.ChoiceField(
        choices=[('', '—— Selecciona empresa ——'),
                 ('empresa1', 'Empresa 1'),
                 ('empresa2', 'Empresa 2'),
                 ('empresa3', 'Empresa 3'),
                 ('empresa4', 'Empresa 4'),
                 ('empresa5', 'Empresa 5')],
        label='Empresa',
        widget=forms.Select(attrs={'class': 'form-control'})
    )