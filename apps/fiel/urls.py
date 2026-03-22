from django.urls import path
from . import views

app_name = 'fiel'
urlpatterns = [
    path('', views.carga_fiel, name='carga_fiel'),
    path('eliminar/<int:carga_id>/', views.eliminar_carga, name='eliminar_carga'),
    path('descargar/<int:carga_id>/<str:tipo>/', views.descargar_archivo, name='descargar_archivo'),
    path('validar/<int:carga_id>/', views.validar_fiel, name='validar_fiel'),

]