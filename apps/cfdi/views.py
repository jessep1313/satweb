from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.signing import loads
from django.apps import apps
import tempfile
import os
from datetime import date
from satcfdi.models import Signer
from satcfdi.pacs.sat import SAT, TipoDescargaMasivaTerceros, EstadoComprobante

from apps.core.decorators import cliente_required
from .models import PeticionSat
from .forms import PeticionSatForm

@cliente_required
def peticion_sat(request):
    # Obtener el modelo CargaFiel de la app 'fiel' sin importarlo directamente
    CargaFiel = apps.get_model('fiel', 'CargaFiel')

    empresa_db = request.session.get('empresa_db')
    rfc_cliente = request.session.get('user_rfc')
    if not empresa_db or not rfc_cliente:
        messages.error(request, 'No se pudo identificar al cliente.')
        return redirect('cliente_dashboard')

    # Obtener la FIEL del cliente desde la tabla fiel
    try:
        fiel = CargaFiel.objects.db_manager(empresa_db).get(rfc_cliente=rfc_cliente, estatus='validado')
    except CargaFiel.DoesNotExist:
        messages.error(request, 'No tienes una FIEL válida cargada. Cárgala y valídala primero en el módulo FIEL.')
        return redirect('fiel:carga_fiel')

    if request.method == 'POST':
        form = PeticionSatForm(request.POST)
        if form.is_valid():
            fechainicio = form.cleaned_data['fechainicio']
            fechafinal = form.cleaned_data['fechafinal']

            if fechafinal > date.today():
                messages.error(request, 'La fecha final no puede ser mayor a hoy.')
                return redirect('cfdi:peticion_sat')

            # Preparar archivos temporales con la FIEL almacenada
            try:
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.cer', delete=False) as cer_temp:
                    cer_temp.write(fiel.archivo_cer.read())
                    cer_path = cer_temp.name

                with tempfile.NamedTemporaryFile(mode='wb', suffix='.key', delete=False) as key_temp:
                    key_temp.write(fiel.archivo_key.read())
                    key_path = key_temp.name

                password = loads(fiel.password)
                signer = Signer.load(
                    certificate=open(cer_path, 'rb').read(),
                    key=open(key_path, 'rb').read(),
                    password=password
                )

                sat = SAT(signer=signer)
                respuesta = sat.recover_comprobante_received_request(
                    fecha_inicial=fechainicio,
                    fecha_final=fechafinal,
                    rfc_receptor=signer.rfc,
                    tipo_solicitud=TipoDescargaMasivaTerceros.CFDI,
                    estado_comprobante=EstadoComprobante.VIGENTE
                )

                # Guardar la petición en la base de datos de la empresa
                PeticionSat.objects.db_manager(empresa_db).create(
                    idpeticion=respuesta['IdSolicitud'],
                    estatuspeticion=0,
                    fechainicio=fechainicio,
                    fechafinal=fechafinal,
                    rfc=rfc_cliente,
                    CodEstatus=respuesta.get('CodEstatus', ''),
                    Mensaje=respuesta.get('Mensaje', ''),
                    RfcSolicitante=respuesta.get('RfcSolicitante', ''),
                    tipo='R'
                )
                messages.success(request, f'Petición creada correctamente. ID: {respuesta["IdSolicitud"]}')
                return redirect('cfdi:peticion_sat')

            except Exception as e:
                messages.error(request, f'Error en la petición: {str(e)}')
            finally:
                # Eliminar archivos temporales
                if os.path.exists(cer_path):
                    os.unlink(cer_path)
                if os.path.exists(key_path):
                    os.unlink(key_path)
        else:
            messages.error(request, 'Corrige los errores del formulario.')
    else:
        form = PeticionSatForm(initial={'rfc': rfc_cliente})

    peticiones = PeticionSat.objects.db_manager(empresa_db).filter(rfc=rfc_cliente).order_by('-fechainicio')
    return render(request, 'cfdi/peticion_sat.html', {'form': form, 'peticiones': peticiones})