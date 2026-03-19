from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import LoginForm
from usuarios_tenant.models import Usuario
from .decorators import admin_required,  cliente_required, tenant_user_required # o tenant_user_required



def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            empresa = form.cleaned_data['empresa']

            if empresa:
                # Autenticación manual contra la base de datos de la empresa
                try:
                    user = Usuario.objects.using(empresa).get(use_login=username)
                    if not user.is_active:
                        messages.error(request, 'Usuario inactivo')
                    elif user.check_password(password):
                        # Guardar en sesión manualmente (sin usar login de Django)
                        request.session['user_type'] = 'tenant'
                        request.session['empresa_db'] = empresa
                        request.session['user_id'] = user.use_id
                        request.session['user_login'] = user.use_login
                        request.session['user_tipo'] = user.use_tipo
                        request.session['user_nombre'] = user.use_nombre
                        # Redirigir según el tipo
                        if user.use_tipo == 'Admin':
                            return redirect('admin_dashboard')
                        else:
                            return redirect('cliente_dashboard')
                    else:
                        messages.error(request, 'Contraseña incorrecta')
                except Usuario.DoesNotExist:
                    messages.error(request, 'Usuario no encontrado en esa empresa')
            else:
                # Autenticación normal para usuario Empresa (usando Django)
                from django.contrib.auth import authenticate, login
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



@admin_required
def admin_dashboard(request):
    return render(request, 'core/admin/dashboard.html')


def admin_required(view_func):
    return tenant_user_required(view_func, required_tipo='Admin')


@admin_required
def listado_clientes(request):

    empresa_db = request.session.get('empresa_db')
    try:
        clientes = Usuario.objects.using(empresa_db).filter(use_tipo='Cliente').values(
            'use_id', 'use_login', 'use_nombre', 'use_email', 'use_rfc'
        )
    except Exception as e:
        messages.error(request, f'Error al obtener clientes: {e}')
        clientes = []
    
    return render(request, 'core/admin/listado_clientes.html', {'clientes': clientes, 'empresa': empresa_db})


@admin_required
def crear_cliente(request):    
    empresa_db = request.session.get('empresa_db')
    
    if request.method == 'POST':
        use_login = request.POST.get('username')
        password = request.POST.get('password')
        use_nombre = request.POST.get('nombre')
        use_email = request.POST.get('email')
        use_rfc = request.POST.get('rfc', '')
        
        try:
            Usuario.objects.db_manager(empresa_db).create_user(
                use_login=use_login,
                password=password,
                use_nombre=use_nombre,
                use_email=use_email,
                use_rfc=use_rfc,
                use_tipo='Cliente'
            )
            messages.success(request, 'Cliente creado correctamente')
            return redirect('listado_clientes')
        except Exception as e:
            messages.error(request, f'Error al crear cliente: {e}')
    
    return render(request, 'core/admin/crear_cliente.html')


@admin_required
def eliminar_cliente(request):    
    if request.method == 'POST':
        empresa_db = request.session.get('empresa_db')
        use_id = request.POST.get('use_id')
        
        try:
            deleted, _ = Usuario.objects.db_manager(empresa_db).filter(use_id=use_id, use_tipo='Cliente').delete()
            if deleted:
                messages.success(request, 'Cliente eliminado correctamente')
            else:
                messages.error(request, 'No se encontró el cliente')
        except Exception as e:
            messages.error(request, f'Error al eliminar: {e}')
    
    return redirect('listado_clientes')


@cliente_required
def cliente_dashboard(request):
    """Dashboard del usuario Cliente"""
    return render(request, 'core/cliente/dashboard.html')