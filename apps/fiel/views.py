from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.signing import dumps
from apps.core.decorators import cliente_required
from usuarios_tenant.models import Usuario
from .forms import CargaFielForm
from .models import CargaFiel

@cliente_required
def carga_fiel(request):
    empresa_db = request.session.get('empresa_db')
    rfc_cliente = request.session.get('user_rfc')          # RFC del cliente (único)
    usuario_id = request.session.get('user_id')            # ID del usuario que carga

    if not rfc_cliente or not empresa_db:
        messages.error(request, 'No se pudo identificar al cliente.')
        return redirect('cliente_dashboard')

    # Obtener el objeto Usuario (opcional, para asignarlo como FK)
    usuario = None
    if usuario_id:
        try:
            usuario = Usuario.objects.db_manager(empresa_db).get(use_id=usuario_id)
        except Usuario.DoesNotExist:
            pass

    # Verificar si ya existe una carga para este RFC
    carga_existente = CargaFiel.objects.db_manager(empresa_db).filter(rfc_cliente=rfc_cliente).exists()

    if request.method == 'POST':
        if carga_existente:
            messages.error(request, 'Ya existe una carga FIEL para este RFC. No se permite una nueva carga.')
            return redirect('fiel:carga_fiel')

        form = CargaFielForm(request.POST, request.FILES)
        if form.is_valid():
            password_cifrada = dumps(form.cleaned_data['password'])
            nueva_carga = CargaFiel(
                rfc_cliente=rfc_cliente,
                usuario=usuario,
                archivo_cer=form.cleaned_data['archivo_cer'],
                archivo_key=form.cleaned_data['archivo_key'],
                password=password_cifrada,
                usuario_login=usuario.use_login if usuario else ''
            )
            nueva_carga.save(using=empresa_db)
            messages.success(request, 'Archivos FIEL cargados correctamente.')
            return redirect('fiel:carga_fiel')
        else:
            messages.error(request, 'Error en el formulario. Verifica los archivos.')
    else:
        form = CargaFielForm()

    # Obtener la carga existente (si la hay) para mostrarla en el historial
    cargas = CargaFiel.objects.db_manager(empresa_db).filter(rfc_cliente=rfc_cliente)

    return render(request, 'fiel/carga_fiel.html', {
        'form': form,
        'cargas': cargas,
        'carga_existente': carga_existente
    })


import os
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import CargaFiel

@cliente_required
def eliminar_carga(request, carga_id):
    empresa_db = request.session.get('empresa_db')
    rfc_cliente = request.session.get('user_rfc')
    if not empresa_db or not rfc_cliente:
        messages.error(request, 'No se pudo identificar al cliente.')
        return redirect('cliente_dashboard')

    try:
        carga = CargaFiel.objects.db_manager(empresa_db).get(pk=carga_id, rfc_cliente=rfc_cliente)
    except CargaFiel.DoesNotExist:
        messages.error(request, 'Carga no encontrada.')
        return redirect('fiel:carga_fiel')

    # Eliminar archivos físicos
    if carga.archivo_cer and os.path.isfile(carga.archivo_cer.path):
        os.remove(carga.archivo_cer.path)
    if carga.archivo_key and os.path.isfile(carga.archivo_key.path):
        os.remove(carga.archivo_key.path)

    carga.delete(using=empresa_db)  # Especificar la base de datos
    messages.success(request, 'Carga FIEL eliminada correctamente.')
    return redirect('fiel:carga_fiel')



import os
from django.http import FileResponse, Http404
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from .models import CargaFiel

@cliente_required
def descargar_archivo(request, carga_id, tipo):
    empresa_db = request.session.get('empresa_db')
    rfc_cliente = request.session.get('user_rfc')
    if not empresa_db or not rfc_cliente:
        raise PermissionDenied

    # Usar db_manager para obtener el objeto en la base correcta
    try:
        carga = CargaFiel.objects.db_manager(empresa_db).get(pk=carga_id, rfc_cliente=rfc_cliente)
    except CargaFiel.DoesNotExist:
        raise Http404("Carga no encontrada")

    if tipo == 'cer':
        archivo = carga.archivo_cer
    elif tipo == 'key':
        archivo = carga.archivo_key
    else:
        raise Http404("Tipo de archivo no válido")

    if not archivo or not os.path.isfile(archivo.path):
        raise Http404("Archivo no encontrado")

    return FileResponse(
        archivo.open('rb'),
        as_attachment=True,
        filename=os.path.basename(archivo.name)
    )


from django.core.signing import loads
from satcfdi.models import Signer  # Import correcto


@cliente_required
def validar_fiel(request, carga_id):
    empresa_db = request.session.get('empresa_db')
    rfc_cliente = request.session.get('user_rfc')
    if not empresa_db or not rfc_cliente:
        messages.error(request, 'No se pudo identificar al cliente.')
        return redirect('cliente_dashboard')

    try:
        carga = CargaFiel.objects.db_manager(empresa_db).get(pk=carga_id, rfc_cliente=rfc_cliente)
    except CargaFiel.DoesNotExist:
        messages.error(request, 'Carga no encontrada.')
        return redirect('fiel:carga_fiel')

    # Decifrar contraseña
    from django.core.signing import loads
    password = loads(carga.password)

    # Validar con satcfdi
    from satcfdi.models import Signer
    import tempfile

    try:
        # Crear archivos temporales con los contenidos reales
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.cer', delete=False) as cer_temp:
            cer_temp.write(carga.archivo_cer.read())
            cer_path = cer_temp.name

        with tempfile.NamedTemporaryFile(mode='wb', suffix='.key', delete=False) as key_temp:
            key_temp.write(carga.archivo_key.read())
            key_path = key_temp.name

        signer = Signer.load(
            certificate=open(cer_path, 'rb').read(),
            key=open(key_path, 'rb').read(),
            password=password
        )

        # Si llegamos aquí, es válida
        carga.estatus = 'validado'
        carga.save(using=empresa_db)
        messages.success(request, f'FIEL válida. RFC: {signer.rfc}, Nombre: {signer.legal_name}')

        # Eliminar archivos temporales
        os.unlink(cer_path)
        os.unlink(key_path)

    except Exception as e:
        carga.estatus = 'rechazado'
        carga.save(using=empresa_db)
        messages.error(request, f'FIEL inválida: {str(e)}')

    return redirect('fiel:carga_fiel')

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from .models import ConfiguracionCorreo
from .forms import ConfiguracionCorreoForm

from .models import ConfiguracionCorreo

@cliente_required
def config_correos(request):
    empresa_db = request.session.get('empresa_db')
    rfc_cliente = request.session.get('user_rfc')
    if not empresa_db or not rfc_cliente:
        messages.error(request, 'No se pudo identificar al cliente.')
        return redirect('cliente_dashboard')

    configs = ConfiguracionCorreo.objects.db_manager(empresa_db).filter(
        rfc_cliente=rfc_cliente
    ).order_by('tipo', 'created_at')

    return render(request, 'fiel/config_correos.html', {
        'configs': configs,
        'tipos': ConfiguracionCorreo.TIPOS
    })


from .forms import ConfiguracionCorreoForm

@cliente_required
def crear_config_correo(request):
    empresa_db = request.session.get('empresa_db')
    rfc_cliente = request.session.get('user_rfc')
    if not empresa_db or not rfc_cliente:
        messages.error(request, 'No se pudo identificar al cliente.')
        return redirect('cliente_dashboard')

    if request.method == 'POST':
        form = ConfiguracionCorreoForm(request.POST)
        if form.is_valid():
            tipo = form.cleaned_data['tipo']
            # Verificar si ya existe una configuración de este tipo para este RFC
            exists = ConfiguracionCorreo.objects.db_manager(empresa_db).filter(
                rfc_cliente=rfc_cliente, tipo=tipo
            ).exists()
            if exists:
                messages.error(request, f'Ya existe una configuración para "{dict(ConfiguracionCorreo.TIPOS)[tipo]}".')
            else:
                config = form.save(commit=False)
                config.rfc_cliente = rfc_cliente
                config.save(using=empresa_db)
                messages.success(request, 'Configuración creada correctamente.')
                return redirect('fiel:config_correos')
    else:
        form = ConfiguracionCorreoForm()

    return render(request, 'fiel/crear_config_correo.html', {'form': form})

@cliente_required
def eliminar_config_correo(request, config_id):
    empresa_db = request.session.get('empresa_db')
    rfc_cliente = request.session.get('user_rfc')
    if not empresa_db or not rfc_cliente:
        messages.error(request, 'No se pudo identificar al cliente.')
        return redirect('cliente_dashboard')

    try:
        config = ConfiguracionCorreo.objects.db_manager(empresa_db).get(
            pk=config_id, rfc_cliente=rfc_cliente
        )
        config.delete(using=empresa_db)
        messages.success(request, 'Configuración eliminada.')
    except ConfiguracionCorreo.DoesNotExist:
        messages.error(request, 'Configuración no encontrada.')

    return redirect('fiel:config_correos')



@cliente_required
def editar_config_correo(request, config_id):
    empresa_db = request.session.get('empresa_db')
    rfc_cliente = request.session.get('user_rfc')
    if not empresa_db or not rfc_cliente:
        messages.error(request, 'No se pudo identificar al cliente.')
        return redirect('cliente_dashboard')

    # Obtener la configuración con la base de datos correcta
    try:
        config = ConfiguracionCorreo.objects.db_manager(empresa_db).get(pk=config_id, rfc_cliente=rfc_cliente)
    except ConfiguracionCorreo.DoesNotExist:
        messages.error(request, 'Configuración no encontrada.')
        return redirect('fiel:config_correos')

    if request.method == 'POST':
        form = ConfiguracionCorreoForm(request.POST, instance=config)
        if form.is_valid():
            nuevo_tipo = form.cleaned_data['tipo']
            if nuevo_tipo != config.tipo:
                exists = ConfiguracionCorreo.objects.db_manager(empresa_db).filter(
                    rfc_cliente=rfc_cliente, tipo=nuevo_tipo
                ).exclude(pk=config_id).exists()
                if exists:
                    messages.error(request, f'Ya existe una configuración para "{dict(ConfiguracionCorreo.TIPOS)[nuevo_tipo]}".')
                    return render(request, 'fiel/editar_config_correo.html', {'form': form, 'config': config, 'tipos': ConfiguracionCorreo.TIPOS})

            # Guardar con la base correcta
            config_actualizado = form.save(commit=False)
            config_actualizado.rfc_cliente = rfc_cliente
            config_actualizado.save(using=empresa_db)
            messages.success(request, 'Configuración actualizada correctamente.')
            return redirect('fiel:config_correos')
        else:
            messages.error(request, 'Corrige los errores del formulario.')
    else:
        form = ConfiguracionCorreoForm(instance=config)

    return render(request, 'fiel/editar_config_correo.html', {
        'form': form,
        'config': config,
        'tipos': ConfiguracionCorreo.TIPOS
    })