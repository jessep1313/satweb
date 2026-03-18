from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import LoginForm
from usuarios_tenant.models import Usuario

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            empresa = form.cleaned_data.get('empresa')

            if empresa:
                messages.error(request, 'El acceso con empresa seleccionada aún no está disponible. Por ahora solo puedes acceder como usuario Empresa (sin seleccionar empresa).')
                return render(request, 'core/login.html', {'form': form})

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                request.session['user_type'] = 'empresa'
                return redirect('empresa_dashboard')
            else:
                messages.error(request, 'Usuario o contraseña incorrectos')
        else:
            messages.error(request, 'Corrige los errores del formulario')
    else:
        form = LoginForm()
    return render(request, 'core/login.html', {'form': form})

@login_required
def empresa_dashboard(request):
    return render(request, 'core/empresa/dashboard.html')

@login_required
def listado_admins(request):
    admins = []
    # Lista de bases de datos que tienes definidas en settings
    empresas = ['empresa1', 'empresa2', 'empresa3', 'empresa4', 'empresa5']
    for db_alias in empresas:
        try:
            usuarios = Usuario.objects.using(db_alias).filter(use_tipo='Admin').values(
                'use_login', 'use_nombre', 'use_email', 'use_rfc'
            )
            for u in usuarios:
                admins.append({
                    'empresa': db_alias,
                    'login': u['use_login'],
                    'nombre': u['use_nombre'],
                    'email': u['use_email'],
                    'rfc': u['use_rfc'],
                })
        except Exception as e:
            print(f"Error en {db_alias}: {e}")
    return render(request, 'core/empresa/lista_admins.html', {'admins': admins})

def logout_view(request):
    logout(request)
    return redirect('login')



from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import AdminCreationForm
from usuarios_tenant.models import Usuario

@login_required
def crear_admin(request):
    if request.method == 'POST':
        empresa = request.POST.get('empresa')
        use_login = request.POST.get('username')
        password = request.POST.get('password')
        use_nombre = request.POST.get('nombre')
        use_email = request.POST.get('email')

        if not empresa:
            messages.error(request, 'Debes seleccionar una empresa')
            return render(request, 'core/empresa/crear_admin.html')

        try:
            # Usar db_manager para obtener el manager con la base de datos específica
            Usuario.objects.db_manager(empresa).create_user(
                use_login=use_login,
                password=password,
                use_nombre=use_nombre,
                use_email=use_email,
                use_tipo='Admin'
            )
            messages.success(request, 'Administrador creado correctamente')
            return redirect('listado_admins')
        except Exception as e:
            messages.error(request, f'Error al crear el administrador: {e}')
            return render(request, 'core/empresa/crear_admin.html', {'empresa': empresa})

    return render(request, 'core/empresa/crear_admin.html')
 
@login_required
def eliminar_admin(request):
    if request.method == 'POST':
        empresa = request.POST.get('empresa')
        use_login = request.POST.get('use_login')

        if not empresa or not use_login:
            messages.error(request, 'Faltan datos para eliminar')
            return redirect('listado_admins')

        try:
            # Eliminar directamente usando filter().delete() en la base de datos correcta
            deleted_count, _ = Usuario.objects.db_manager(empresa).filter(use_login=use_login).delete()
            
            if deleted_count > 0:
                messages.success(request, f'Administrador {use_login} eliminado correctamente')
            else:
                messages.error(request, 'No se encontró el administrador')
                
        except Exception as e:
            messages.error(request, f'Error al eliminar: {e}')

    return redirect('listado_admins')