from django.urls import path
from . import views

app_name = 'cfdi'

urlpatterns = [
    path('peticion-sat/', views.peticion_sat, name='peticion_sat'),
]