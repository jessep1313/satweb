import os
import zipfile
import glob
import tempfile
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connections
from django.apps import apps
from django.core.signing import loads

from satcfdi.models import Signer
from satcfdi.pacs.sat import SAT, EstadoSolicitud

import base64

# Diccionarios de códigos (mismos del script original)
FORMAS_PAGO = {
    '01': '01 - Efectivo',
    '02': '02 - Cheque nominativo',
    '03': '03 - Transferencia electrónica de fondos',
    '04': '04 - Tarjeta de crédito',
    '05': '05 - Monedero electrónico',
    '06': '06 - Dinero electrónico',
    '08': '08 - Vales de despensa',
    '12': '12 - Dación en pago',
    '13': '13 - Pago por subrogación',
    '14': '14 - Pago por consignación',
    '15': '15 - Condonación',
    '17': '17 - Compensación',
    '23': '23 - Novación',
    '24': '24 - Confusión',
    '25': '25 - Remisión de deuda',
    '26': '26 - Prescripción o caducidad',
    '27': '27 - A satisfacción del acreedor',
    '28': '28 - Tarjeta de débito',
    '29': '29 - Tarjeta de servicios',
    '30': '30 - Aplicación de anticipos',
    '31': '31 - Intermediario pagos',
    '99': '99 - Por definir'
}

METODOS_PAGO = {
    'PUE': 'PUE - Pago en una sola exhibición',
    'PPD': 'PPD - Pago en parcialidades o diferido'
}

class Command(BaseCommand):
    help = 'Procesa peticiones SAT: verifica estado, descarga paquetes y carga CFDI'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa',
            type=str,
            help='Procesar solo una empresa específica (ej. empresa1)',
        )

    def handle(self, *args, **options):
        # Obtener todas las bases de datos que empiecen con 'empresa'
        if options['empresa']:
            bases = [options['empresa']]
        else:
            bases = [db for db in settings.DATABASES.keys() if db.startswith('empresa')]

        for db_alias in bases:
            self.stdout.write(self.style.SUCCESS(f"\n--- Procesando base: {db_alias} ---"))
            try:
                self.procesar_empresa(db_alias)
            except Exception as e:
                self.stderr.write(f"Error en {db_alias}: {e}")

    def procesar_empresa(self, db_alias):
        # 1. Procesar peticiones pendientes de descarga (estatuspeticion = 0)
        self.procesar_descargas(db_alias)

        # 2. Procesar peticiones pendientes de carga XML (estatuspeticion = 1 y cargadoxml = 0)
        self.procesar_xml(db_alias)

    def procesar_descargas(self, db_alias):
        CargaFiel = apps.get_model('fiel', 'CargaFiel')

        with connections[db_alias].cursor() as cursor:
            cursor.execute("""
                SELECT idpeticion, rfc, fechainicio
                FROM peticiones_sat
                WHERE estatuspeticion = 0
                ORDER BY fechainicio DESC
            """)
            peticiones = cursor.fetchall()

        self.stdout.write(f"  Peticiones pendientes de descarga: {len(peticiones)}")

        for id_peticion, rfc_cliente, fechainicio in peticiones:
            self.stdout.write(f"    Procesando petición {id_peticion} para RFC {rfc_cliente}")

            # Obtener FIEL del cliente
            try:
                fiel = CargaFiel.objects.using(db_alias).get(rfc_cliente=rfc_cliente, estatus='validado')
            except CargaFiel.DoesNotExist:
                self.stderr.write(f"      No se encontró FIEL válida para {rfc_cliente}")
                continue

            cer_path = None
            key_path = None
            try:
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.cer', delete=False) as cer_tmp:
                    cer_tmp.write(fiel.archivo_cer.read())
                    cer_path = cer_tmp.name
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.key', delete=False) as key_tmp:
                    key_tmp.write(fiel.archivo_key.read())
                    key_path = key_tmp.name

                password = loads(fiel.password)
                signer = Signer.load(
                    certificate=open(cer_path, 'rb').read(),
                    key=open(key_path, 'rb').read(),
                    password=password
                )

                sat = SAT(signer=signer)
                respuesta = sat.recover_comprobante_status(id_peticion)

                estado = respuesta.get("EstadoSolicitud")
                if estado == EstadoSolicitud.TERMINADA:
                    ids_paquetes = respuesta.get('IdsPaquetes', [])
                    if ids_paquetes:
                        # fechainicio puede ser string o date
                        if isinstance(fechainicio, str):
                            fecha = datetime.strptime(fechainicio, '%Y-%m-%d').date()
                        else:
                            fecha = fechainicio
                        folder = Path(settings.MEDIA_ROOT) / 'cfdi' / rfc_cliente / str(fecha.year) / f"{fecha.month:02d}"
                        folder.mkdir(parents=True, exist_ok=True)

                        descargados = 0
                        for id_paquete in ids_paquetes:
                            try:
                                respuesta, paquete_base64 = sat.recover_comprobante_download(id_paquete)
                                paquete_bytes = base64.b64decode(paquete_base64)
                                with open(folder / f"{id_paquete}.zip", 'wb') as f:
                                    f.write(paquete_bytes)
                                descargados += 1
                                self.stdout.write(f"        Paquete {id_paquete} descargado")
                            except Exception as e:
                                self.stderr.write(f"        Error descargando {id_paquete}: {e}")

                        if descargados > 0:
                            with connections[db_alias].cursor() as cursor_upd:
                                cursor_upd.execute(
                                    "UPDATE peticiones_sat SET estatuspeticion = 1 WHERE idpeticion = %s",
                                    [id_peticion]
                                )
                            self.stdout.write(f"      Petición {id_peticion} marcada como descargada")
                    else:
                        self.stdout.write(f"      Petición terminada sin paquetes")
                elif estado in (EstadoSolicitud.ACEPTADA, EstadoSolicitud.EN_PROCESO):
                    self.stdout.write(f"      Petición aún en proceso")
                else:
                    self.stdout.write(f"      Petición falló: {respuesta.get('CodEstatus')} - {respuesta.get('Mensaje')}")

            except Exception as e:
                self.stderr.write(f"      Error procesando petición {id_peticion}: {e}")
            finally:
                if cer_path and os.path.exists(cer_path):
                    os.unlink(cer_path)
                if key_path and os.path.exists(key_path):
                    os.unlink(key_path)

    def procesar_xml(self, db_alias):
        with connections[db_alias].cursor() as cursor:
            cursor.execute("""
                SELECT idpeticion, rfc, fechainicio, fechafinal
                FROM peticiones_sat
                WHERE estatuspeticion = 1 AND cargadoxml = 0
                ORDER BY fechainicio DESC
            """)
            peticiones = cursor.fetchall()

        self.stdout.write(f"  Peticiones pendientes de procesamiento XML: {len(peticiones)}")

        for id_peticion, rfc_cliente, fechainicio, fechafinal in peticiones:

            self.stdout.write(f"    Procesando XML de petición {id_peticion} (RFC: {rfc_cliente})")

            # Buscar ZIP descargados
            if isinstance(fechainicio, str):
                fecha = datetime.strptime(fechainicio, '%Y-%m-%d').date()
            else:
                fecha = fechainicio
            # También convertir fechafinal para usarlo en registrar_proveedor
            if isinstance(fechafinal, str):
                fecha_final = datetime.strptime(fechafinal, '%Y-%m-%d').date()
            else:
                fecha_final = fechafinal

                
            zip_pattern = Path(settings.MEDIA_ROOT) / 'cfdi' / rfc_cliente / str(fecha.year) / f"{fecha.month:02d}" / '*.zip'
            zips = glob.glob(str(zip_pattern))

            if not zips:
                self.stdout.write(f"      No se encontraron ZIP para {id_peticion}")
                continue

            stats = {
                'xml_procesados': 0,
                'facturas_insertadas': 0,
                'complementos_insertados': 0,
                'facturas_existentes': 0,
                'errores': 0,
                'proveedores_registrados': 0
            }

            with connections[db_alias].cursor() as cursor_ins:
                for zip_path in zips:
                    temp_dir = tempfile.mkdtemp()
                    try:
                        with zipfile.ZipFile(zip_path, 'r') as zf:
                            zf.extractall(temp_dir)

                        for root_dir, _, files in os.walk(temp_dir):
                            for file in files:
                                if not file.lower().endswith('.xml'):
                                    continue
                                xml_path = os.path.join(root_dir, file)
                                datos = self.extraer_datos_factura(xml_path, rfc_cliente, fechafinal)
                                if datos and 'error' not in datos:
                                    stats['xml_procesados'] += 1
                                    # Insertar en cfdi_<rfc_cliente>
                                    resultado = self.insertar_cfdi(cursor_ins, rfc_cliente, datos)
                                    if resultado == 'insertado':
                                        if datos.get('tipo_cfdi') == 'complemento_pago':
                                            stats['complementos_insertados'] += 1
                                        else:
                                            stats['facturas_insertadas'] += 1
                                    elif resultado == 'existe':
                                        stats['facturas_existentes'] += 1
                                    else:
                                        stats['errores'] += 1

                                    # Registrar proveedor (solo para facturas normales)
                                    if datos.get('tipo_cfdi') == 'factura':
                                        self.registrar_proveedor(cursor_ins, rfc_cliente, datos, fechafinal)
                                elif datos and 'error' in datos:
                                    stats['errores'] += 1
                                    self.stderr.write(f"        Error en {file}: {datos['error']}")
                    except Exception as e:
                        self.stderr.write(f"      Error procesando ZIP {zip_path}: {e}")
                    finally:
                        shutil.rmtree(temp_dir, ignore_errors=True)

            # Marcar petición como procesada si se insertaron comprobantes
            if stats['facturas_insertadas'] > 0 or stats['complementos_insertados'] > 0:
                with connections[db_alias].cursor() as cursor_upd:
                    cursor_upd.execute(
                        "UPDATE peticiones_sat SET cargadoxml = 1 WHERE idpeticion = %s",
                        [id_peticion]
                    )
                self.stdout.write(f"      Petición {id_peticion} marcada como procesada (XML cargados)")

    def extraer_datos_factura(self, xml_path, rfc_receptor, fecha_peticion):
        """Extrae datos del XML similar al script original"""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            ns = {
                'cfdi': 'http://www.sat.gob.mx/cfd/4',
                'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
                'pago10': 'http://www.sat.gob.mx/Pagos',
                'pago20': 'http://www.sat.gob.mx/Pagos20'
            }

            # Verificar receptor
            receptor = root.find('cfdi:Receptor', ns)
            if receptor is None or receptor.get('Rfc') != rfc_receptor:
                return None

            # Determinar tipo
            complemento_pago = root.find('.//pago10:Pagos', ns) or root.find('.//pago20:Pagos', ns)
            if complemento_pago is not None:
                return self.procesar_complemento_pago(root, ns, rfc_receptor, fecha_peticion)
            else:
                return self.procesar_factura_normal(root, ns, rfc_receptor, fecha_peticion)

        except ET.ParseError as e:
            return {'error': f'XML inválido: {e}'}
        except Exception as e:
            return {'error': str(e)}

    def procesar_factura_normal(self, root, ns, rfc_receptor, fecha_peticion):
        """Procesa factura normal"""
        emisor = root.find('cfdi:Emisor', ns)
        rfc_emisor = emisor.get('Rfc') if emisor is not None else ''
        nombre_emisor = emisor.get('Nombre') if emisor is not None else ''

        subtotal = root.get('SubTotal', '0.00')
        total = root.get('Total', '0.00')
        iva = '0.00'

        impuestos = root.find('cfdi:Impuestos', ns)
        if impuestos is not None:
            traslados = impuestos.find('cfdi:Traslados', ns)
            if traslados is not None:
                for traslado in traslados.findall('cfdi:Traslado', ns):
                    if traslado.get('Impuesto') == '002':
                        iva = traslado.get('Importe', '0.00')
                        break

        forma_pago_cod = root.get('FormaPago', '99')
        forma_pago_desc = FORMAS_PAGO.get(forma_pago_cod, f"{forma_pago_cod} - Desconocido")
        metodo_pago_cod = root.get('MetodoPago', 'PPD')
        metodo_pago_desc = METODOS_PAGO.get(metodo_pago_cod, f"{metodo_pago_cod} - Desconocido")

        datos = {
            'tipo_cfdi': 'factura',
            'rfc_emisor': rfc_emisor,
            'rfc_receptor': rfc_receptor,
            'folio': root.get('Folio'),
            'uudi': None,
            'fecha_comprobante': root.get('Fecha')[:10] if root.get('Fecha') else None,
            'total': total,
            'Iva': iva,
            'Suma': f"{float(subtotal) + float(iva):.2f}",
            'status_sat': 'R',
            'moneda': root.get('Moneda', 'MXN'),
            'tipo_cambio': root.get('TipoCambio', '1.0'),
            'forma_pago': forma_pago_desc,
            'metodo_pago': metodo_pago_desc,
            'fecha_timbrado': None,
            'saldo_pendiente': total,
            'situacion_interna_externa': '',
            'complemento_pago': '',
            'fecha_cancelacion': '',
            'estado_factura': '',
            'num_complemento': '',
            'nombre_emisor': nombre_emisor
        }

        timbre = root.find('cfdi:Complemento//tfd:TimbreFiscalDigital', ns)
        if timbre is not None:
            datos['uudi'] = timbre.get('UUID')
            datos['fecha_timbrado'] = timbre.get('FechaTimbrado')[:10] if timbre.get('FechaTimbrado') else None

        return datos

    def procesar_complemento_pago(self, root, ns, rfc_receptor, fecha_peticion):
        """Procesa complemento de pago"""
        emisor = root.find('cfdi:Emisor', ns)
        rfc_emisor = emisor.get('Rfc') if emisor is not None else ''
        nombre_emisor = emisor.get('Nombre') if emisor is not None else ''

        pagos = root.find('.//pago10:Pagos', ns) or root.find('.//pago20:Pagos', ns)
        monto_total = '0.00'
        fecha_pago = None
        num_operacion = ''
        uuids_relacionados = []

        if pagos is not None:
            pago = pagos.find('.//pago10:Pago', ns) or pagos.find('.//pago20:Pago', ns)
            if pago is not None:
                monto_total = pago.get('Monto', '0.00')
                fecha_pago = pago.get('FechaPago')
                num_operacion = pago.get('NumOperacion', '')
                doctos = pago.findall('.//pago10:DoctoRelacionado', ns) or pago.findall('.//pago20:DoctoRelacionado', ns)
                for docto in doctos:
                    uuid = docto.get('IdDocumento')
                    if uuid:
                        uuids_relacionados.append(uuid)

        forma_pago_cod = root.get('FormaPago', '99')
        forma_pago_desc = FORMAS_PAGO.get(forma_pago_cod, f"{forma_pago_cod} - Desconocido")

        datos = {
            'tipo_cfdi': 'complemento_pago',
            'rfc_emisor': rfc_emisor,
            'rfc_receptor': rfc_receptor,
            'folio': root.get('Folio') or f"CP-{num_operacion}",
            'uudi': None,
            'fecha_comprobante': fecha_pago[:10] if fecha_pago else root.get('Fecha')[:10] if root.get('Fecha') else None,
            'total': monto_total,
            'moneda': root.get('Moneda', 'MXN'),
            'forma_pago': forma_pago_desc,
            'uso_cfdi': receptor.get('UsoCFDI', '') if (receptor := root.find('cfdi:Receptor', ns)) else '',
            'uudirelacion': ','.join(uuids_relacionados),
            'Iva': '0.00',
            'Suma': monto_total,
            'status_sat': 'R',
            'tipo_cambio': root.get('TipoCambio', '1.0'),
            'metodo_pago': '',
            'fecha_timbrado': None,
            'saldo_pendiente': monto_total,
            'situacion_interna_externa': '',
            'complemento_pago': 'SI',
            'fecha_cancelacion': '',
            'estado_factura': '',
            'num_complemento': num_operacion,
            'nombre_emisor': nombre_emisor
        }

        timbre = root.find('cfdi:Complemento//tfd:TimbreFiscalDigital', ns)
        if timbre is not None:
            datos['uudi'] = timbre.get('UUID')
            datos['fecha_timbrado'] = timbre.get('FechaTimbrado')[:10] if timbre.get('FechaTimbrado') else None

        return datos

    def insertar_cfdi(self, cursor, rfc_cliente, datos):
        """Inserta un CFDI en la tabla cfdi_<rfc>"""
        tabla = f"cfdi_{rfc_cliente}"
        uuid = datos.get('uudi')

        # Verificar duplicado
        cursor.execute(f"SELECT COUNT(*) FROM {tabla} WHERE uudi = %s", [uuid])
        if cursor.fetchone()[0] > 0:
            return 'existe'

        sql = f"""
            INSERT INTO {tabla} (
                rfc_emisor, rfc_receptor, folio, uudi, fecha_comprobante,
                total, Iva, Suma, status_sat, moneda, situacion_interna_externa,
                complemento_pago, forma_pago, metodo_pago, fecha_cancelacion,
                tipo_cambio, fecha_timbrado, estado_factura, saldo_pendiente,
                num_complemento
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        valores = (
            datos['rfc_emisor'], datos['rfc_receptor'], datos['folio'], uuid,
            datos['fecha_comprobante'], datos['total'], datos['Iva'], datos['Suma'],
            datos['status_sat'], datos['moneda'], datos.get('situacion_interna_externa', ''),
            datos.get('complemento_pago', ''), datos['forma_pago'], datos.get('metodo_pago', ''),
            datos.get('fecha_cancelacion', ''), datos['tipo_cambio'], datos.get('fecha_timbrado', ''),
            datos.get('estado_factura', ''), datos.get('saldo_pendiente', datos['total']),
            datos.get('num_complemento', '')
        )
        try:
            cursor.execute(sql, valores)
            return 'insertado'
        except Exception as e:
            self.stderr.write(f"      Error insertando en {tabla}: {e}")
            return 'error'

    def registrar_proveedor(self, cursor, rfc_cliente, datos, fecha_peticion):
        """Registra un proveedor en proveedores_<rfc> si no existe"""
        tabla = f"proveedores_{rfc_cliente}"
        rfc_prov = datos.get('rfc_emisor')
        nombre_prov = datos.get('nombre_emisor')
        if not rfc_prov or not nombre_prov:
            return

        # Verificar duplicado (por RFC + rfc_identy)
        cursor.execute(f"SELECT COUNT(*) FROM {tabla} WHERE RFC = %s AND rfc_identy = %s", [rfc_prov, rfc_cliente])
        if cursor.fetchone()[0] > 0:
            return

        if isinstance(fecha_peticion, str):
            fecha_dt = datetime.strptime(fecha_peticion, '%Y-%m-%d')
        else:
            fecha_dt = fecha_peticion  # asumiendo que es date o datetime
        ano_reg = fecha_dt.year
        mes_reg = fecha_dt.month

        sql = f"""
            INSERT INTO {tabla} (
                RFC, RazonSocial, Estatus, tipoProveedor, Correo,
                rfc_identy
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        valores = (
            rfc_prov,
            nombre_prov,
            'SinRespuesta',
            '0tro',
            'generico@generico.com',
            rfc_cliente
        )
        try:
            cursor.execute(sql, valores)
            self.stdout.write(f"        Proveedor registrado: {rfc_prov} - {nombre_prov}")
        except Exception as e:
            self.stderr.write(f"        Error registrando proveedor {rfc_prov}: {e}")