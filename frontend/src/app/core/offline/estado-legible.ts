import { OperacionLocal } from '../offline.models';

/** Frase clara para una operación que todavía no se confirmó (en vez de «REGISTRADA_LOCAL» o «Compra local c20069dd»). */
export function estadoLegible(o: Pick<OperacionLocal, 'tipo' | 'estado' | 'resumen'>): string {
  if (o.estado === 'ENVIADA') return 'Enviando al servidor…';
  const tarjeta = /se cobrará a (.+?) terminada en (\d{4})/.exec(o.resumen ?? '');
  if (o.tipo === 'COMPRA') return tarjeta ? `Pendiente de enviar · se cobrará a la ${tarjeta[1]} ${tarjeta[2]} al reconectar` : 'Pendiente de enviar · quedará por pagar al reconectar';
  return 'Pendiente de enviar · se enviará al reconectar';
}
