import { OperacionLocal } from '../offline.models';

/** B1 · Número local `LOC-<sucursal>-<6 del UUID>`; al sincronizar, la venta recibe su número oficial CMP-…. */
export const numeroLocal = (o: OperacionLocal) => `LOC-${String(o.sucursal_id ?? 0).padStart(3, '0')}-${o.id.replace(/-/g, '').slice(0, 6).toUpperCase()}`;

/** Comprobante provisional de una venta de contado hecha sin conexión, armado en el navegador. Es válido una vez sincronizada la venta. */
export async function comprobanteProvisional(o: OperacionLocal, empresa: string, nombreDe: (varianteId: number) => string) {
  const { jsPDF } = await import('jspdf');  // se carga solo al pedir el comprobante
  const items = (o.payload['items'] as { variante_id: number; cantidad: number; precio_unitario: string }[]) ?? [];
  const doc = new jsPDF({ format: 'a5' });
  let y = 15;
  doc.setFontSize(14); doc.text(empresa, 10, y); y += 7;
  doc.setFontSize(10); doc.text(`Comprobante provisional ${numeroLocal(o)}`, 10, y); y += 5;
  doc.text(`Fecha: ${new Date(o.creada_en).toLocaleString('es-BO')}`, 10, y); y += 5;
  doc.text('Pendiente de sincronizar: será válido al confirmarse la venta.', 10, y); y += 9;
  let total = 0;
  for (const i of items) {
    const subtotal = Number(i.precio_unitario) * i.cantidad; total += subtotal;
    doc.text(`${i.cantidad} × ${nombreDe(i.variante_id)}`.slice(0, 48), 10, y); doc.text(subtotal.toFixed(2), 130, y, { align: 'right' }); y += 5;
  }
  y += 3; doc.setFontSize(11); doc.text(`Total: Bs ${total.toFixed(2)}`, 10, y); y += 5;
  const recibido = Number(o.payload['monto_recibido'] ?? 0);
  doc.text(`Recibido: Bs ${recibido.toFixed(2)}   Cambio: Bs ${Math.max(recibido - total, 0).toFixed(2)}`, 10, y);
  return doc;
}
