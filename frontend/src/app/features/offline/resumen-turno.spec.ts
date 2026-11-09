import { describe, expect, it } from 'vitest';
import { OperacionLocal } from '../../core/offline.models';
import { resumirTurno } from './resumen-turno.component';

const op = (id: string, estado: OperacionLocal['estado'], recibido: string, items: { cantidad: number; precio_unitario: string }[], tipo: OperacionLocal['tipo'] = 'VENTA_CONTADO'): OperacionLocal => ({
  id, empresa_id: 1, sucursal_id: 1, usuario_id: 5, tipo, estado, intentos: 0, mensaje: '', referencia: null, comprobante: null, detalle: null, creada_en: 'x', resumen: '',
  payload: { items, monto_recibido: recibido },
});

describe('Resumen de mi turno (B2)', () => {
  it('cuenta ventas, efectivo, cambio y estados, e ignora lo que no es venta', () => {
    const r = resumirTurno([
      op('a', 'CONFIRMADA', '100.00', [{ cantidad: 2, precio_unitario: '40.00' }]),
      op('b', 'REGISTRADA_LOCAL', '50.00', [{ cantidad: 1, precio_unitario: '45.00' }]),
      op('c', 'EN_CONFLICTO', '200.00', [{ cantidad: 1, precio_unitario: '190.00' }]),
      op('d', 'CONFIRMADA', '0', [], 'RESERVA'),
    ]);
    expect([r.ventas, r.recibido, r.total, r.cambio]).toEqual([3, 350, 315, 35]);
    expect([r.por_estado['CONFIRMADA'], r.por_estado['REGISTRADA_LOCAL'], r.por_estado['EN_CONFLICTO'], r.por_estado['RECHAZADA']]).toEqual([1, 1, 1, 0]);
  });
});
