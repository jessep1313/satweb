from django import forms

class PeticionSatForm(forms.Form):
    fechainicio = forms.DateField(
        label="Fecha inicio",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    fechafinal = forms.DateField(
        label="Fecha final",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    rfc = forms.CharField(
        label="RFC",
        required=False,
        disabled=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )