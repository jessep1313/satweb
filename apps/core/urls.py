from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('dashboard/', views.empresa_dashboard, name='empresa_dashboard'),
    path('empresas/listado-admins/', views.listado_admins, name='listado_admins'),
    path('logout/', views.logout_view, name='logout'),
    path('empresas/crear-admin/', views.crear_admin, name='crear_admin'),
    path('empresas/eliminar-admin/', views.eliminar_admin, name='eliminar_admin'),

    path('panel-admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('panel-admin/clientes/', views.listado_clientes, name='listado_clientes'),
    path('panel-admin/clientes/crear/', views.crear_cliente, name='crear_cliente'),
    path('panel-admin/clientes/eliminar/', views.eliminar_cliente, name='eliminar_cliente'),

    path('cliente-dashboard/', views.cliente_dashboard, name='cliente_dashboard'),


]