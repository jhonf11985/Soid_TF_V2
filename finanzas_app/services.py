# finanzas_app/services.py

import uuid
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import MovimientoFinanciero, CategoriaMovimiento, CuentaFinanciera


class TransferenciaService:
    """
    Servicio para manejar transferencias entre cuentas.
    Encapsula toda la lógica de negocio.
    """
    
    @staticmethod
    def validar_saldo_disponible(cuenta, monto):
        """
        Calcula el saldo actual de una cuenta y verifica si tiene fondos suficientes.
        Retorna (saldo_actual, tiene_fondos, mensaje)
        """
        from django.db.models import Sum, Q
        
        # Calcular saldo actual
        totales = MovimientoFinanciero.objects.filter(
            cuenta=cuenta
        ).exclude(estado="anulado").aggregate(
            ingresos=Sum("monto", filter=Q(tipo="ingreso")),
            egresos=Sum("monto", filter=Q(tipo="egreso")),
        )
        
        ingresos = totales.get("ingresos") or Decimal("0")
        egresos = totales.get("egresos") or Decimal("0")
        saldo_actual = cuenta.saldo_inicial + ingresos - egresos
        
        tiene_fondos = saldo_actual >= monto
        
        if not tiene_fondos:
            mensaje = (
                f"La cuenta '{cuenta.nombre}' no tiene fondos suficientes. "
                f"Saldo actual: {cuenta.moneda} {saldo_actual:.2f}, "
                f"Monto requerido: {cuenta.moneda} {monto:.2f}"
            )
        else:
            mensaje = None
        
        return saldo_actual, tiene_fondos, mensaje
    
    @staticmethod
    def crear_transferencia(
        cuenta_origen,
        cuenta_destino,
        monto,
        fecha,
        usuario,
        descripcion="",
        referencia="",
        validar_saldo=True
    ):
        """
        Crea una transferencia entre dos cuentas.
        
        Params:
            cuenta_origen: CuentaFinanciera de donde sale el dinero
            cuenta_destino: CuentaFinanciera donde entra el dinero
            monto: Decimal con el monto a transferir
            fecha: date de la transferencia
            usuario: User que realiza la operación
            descripcion: str opcional
            referencia: str opcional
            validar_saldo: bool, si True valida que haya fondos (default True)
        
        Returns:
            tuple (movimiento_envio, movimiento_recepcion)
        
        Raises:
            ValidationError si algo falla
        """
        
        # Validación básica
        if cuenta_origen == cuenta_destino:
            raise ValidationError("No puedes transferir a la misma cuenta.")
        
        if cuenta_origen.moneda != cuenta_destino.moneda:
            raise ValidationError(
                f"Las cuentas deben ser de la misma moneda. "
                f"Origen: {cuenta_origen.moneda}, Destino: {cuenta_destino.moneda}."
            )
        
        if monto <= 0:
            raise ValidationError("El monto debe ser mayor a cero.")
        
        # Validar saldo si está habilitado
        if validar_saldo:
            saldo_actual, tiene_fondos, mensaje = TransferenciaService.validar_saldo_disponible(
                cuenta_origen, monto
            )
            if not tiene_fondos:
                raise ValidationError(mensaje)
        
        # Obtener categorías especiales
        try:
            categoria_enviada = CategoriaMovimiento.objects.get(
                nombre="Transferencia enviada",
                tipo="egreso"
            )
        except CategoriaMovimiento.DoesNotExist:
            raise ValidationError(
                "No se encontró la categoría 'Transferencia enviada'. "
                "Ejecuta las migraciones correctamente."
            )
        
        try:
            categoria_recibida = CategoriaMovimiento.objects.get(
                nombre="Transferencia recibida",
                tipo="ingreso"
            )
        except CategoriaMovimiento.DoesNotExist:
            raise ValidationError(
                "No se encontró la categoría 'Transferencia recibida'. "
                "Ejecuta las migraciones correctamente."
            )
        
        # Generar UUID compartido
        transferencia_uuid = uuid.uuid4()
        
        # Descripción mejorada si no se proporcionó
        if not descripcion:
            descripcion = f"Transferencia de {cuenta_origen.nombre} a {cuenta_destino.nombre}"
        
        # Crear ambos movimientos en una transacción atómica
        try:
            with transaction.atomic():
                # Movimiento 1: EGRESO en cuenta origen
                movimiento_envio = MovimientoFinanciero.objects.create(
                    fecha=fecha,
                    tipo="egreso",
                    cuenta=cuenta_origen,
                    categoria=categoria_enviada,
                    monto=monto,
                    descripcion=descripcion,
                    referencia=referencia,
                    es_transferencia=True,
                    transferencia_id=transferencia_uuid,
                    creado_por=usuario,
                    estado="confirmado"
                )
                
                # Movimiento 2: INGRESO en cuenta destino
                movimiento_recepcion = MovimientoFinanciero.objects.create(
                    fecha=fecha,
                    tipo="ingreso",
                    cuenta=cuenta_destino,
                    categoria=categoria_recibida,
                    monto=monto,
                    descripcion=descripcion,
                    referencia=referencia,
                    es_transferencia=True,
                    transferencia_id=transferencia_uuid,
                    creado_por=usuario,
                    estado="confirmado"
                )
                
                return (movimiento_envio, movimiento_recepcion)
        
        except Exception as e:
            raise ValidationError(f"Error al crear la transferencia: {str(e)}")
    
    @staticmethod
    def anular_transferencia(movimiento):
        """
        Anula una transferencia completa (ambos movimientos).
        
        Params:
            movimiento: cualquiera de los dos MovimientoFinanciero de la transferencia
        
        Returns:
            tuple (mov_envio_anulado, mov_recepcion_anulado)
        
        Raises:
            ValidationError si no es una transferencia
        """
        if not movimiento.es_transferencia:
            raise ValidationError("Este movimiento no es una transferencia.")
        
        if not movimiento.transferencia_id:
            raise ValidationError("Este movimiento no tiene ID de transferencia.")
        
        # Buscar ambos movimientos de la transferencia
        movimientos = MovimientoFinanciero.objects.filter(
            transferencia_id=movimiento.transferencia_id
        )
        
        if movimientos.count() != 2:
            raise ValidationError(
                f"Se esperaban 2 movimientos pero se encontraron {movimientos.count()}."
            )
        
        # Anular ambos en transacción atómica
        try:
            with transaction.atomic():
                for mov in movimientos:
                    mov.estado = "anulado"
                    mov.save()
                
                return tuple(movimientos)
        
        except Exception as e:
            raise ValidationError(f"Error al anular la transferencia: {str(e)}")