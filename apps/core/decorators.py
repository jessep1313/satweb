from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps




def tenant_user_required(view_func=None, required_tipo=None):
    """
    Decorador para vistas de tenant (Admin o Cliente).
    Verifica que el usuario tenga sesión de tenant y opcionalmente un tipo específico.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            print('user_type:', request.session.get('user_type'))
            print('user_tipo:', request.session.get('user_tipo'))
            if request.session.get('user_type') != 'tenant':
                messages.error(request, 'Debes iniciar sesión como usuario de empresa')
                return redirect('login')
            if required_tipo and request.session.get('user_tipo') != required_tipo:
                messages.error(request, 'No tienes permiso para acceder a esta página')
                return redirect('login')
            return view_func(request, *args, **kwargs)
        return _wrapped_view

    if view_func:
        return decorator(view_func)
    return decorator




def admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.session.get('user_type') != 'tenant' or request.session.get('user_tipo') != 'Admin':
            messages.error(request, 'No tienes permiso para acceder a esta página')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped


    

def cliente_required(view_func):
    """Decorador para vistas que requieren usuario Cliente (tenant)."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.session.get('user_type') == 'tenant' and request.session.get('user_tipo') == 'Cliente':
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Acceso no autorizado')
        return redirect('login')
    return _wrapped_view

def empresa_required(view_func):
    """Decorador para vistas que requieren usuario Empresa."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.session.get('user_type') == 'empresa':
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Acceso no autorizado')
        return redirect('login')
    return _wrapped_view

def user_type(request):
    return {'user_type': request.session.get('user_type')}





def cliente_required(view_func):
    """Decorador para vistas que solo pueden acceder clientes"""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.session.get('user_type') != 'tenant' or request.session.get('user_tipo') not in ('Cliente', 'Empleado'):
            messages.error(request, 'No tienes permiso para acceder a esta página')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped

