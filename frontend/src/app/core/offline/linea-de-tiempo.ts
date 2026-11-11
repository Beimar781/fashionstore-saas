import { IntentoSync } from './local-db.service';
import { OperacionLocal } from '../offline.models';

export interface PasoTiempo { fecha: string | null; texto: string; tipo: 'info' | 'ok' | 'warn' | 'danger'; }

/** Nombre corto del dispositivo («Chrome en Windows») para la línea de tiempo. */
export function etiquetaDispositivo(agente = typeof navigator === 'undefined' ? '' : navigator.userAgent): string {
  const navegador = /Edg\//.test(agente) ? 'Edge' : /OPR\//.test(agente) ? 'Opera' : /Firefox\//.test(agente) ? 'Firefox' : /Chrome\//.test(agente) ? 'Chrome' : /Safari\//.test(agente) ? 'Safari' : 'Navegador';
  const sistema = /Android/.test(agente) ? 'Android' : /iPhone|iPad/.test(agente) ? 'iOS' : /Windows/.test(agente) ? 'Windows' : /Mac OS/.test(agente) ? 'macOS' : /Linux/.test(agente) ? 'Linux' : 'este equipo';
  return `${navegador} en ${sistema}`;
}

/**
 * Historia de una operación sin conexión: registrada en este dispositivo → enviada (cada intento, con su resultado) → confirmada, en conflicto o rechazada → resuelta.
 * Sale de lo guardado en el dispositivo (la operación y el registro de sincronización), así que se puede ver sin conexión.
 */
export function lineaDeTiempo(o: OperacionLocal, registro: IntentoSync[], dispositivo = etiquetaDispositivo()): PasoTiempo[] {
  const pasos: PasoTiempo[] = [{ fecha: o.creada_en, texto: `Registrada en este dispositivo (${dispositivo})`, tipo: 'info' }];
  const intentos = registro.filter((r) => r.operacion_id === o.id).sort((a, b) => a.fecha.localeCompare(b.fecha));
  for (const i of intentos) {
    const envio = `Envío ${i.intento}`;
    if (i.resultado === 'CONFIRMADA') pasos.push({ fecha: i.fecha, texto: `${envio}: confirmada por el servidor`, tipo: 'ok' });
    else if (i.resultado === 'EN_CONFLICTO') pasos.push({ fecha: i.fecha, texto: `${envio}: en conflicto${i.motivo ? ' — ' + i.motivo : ''}`, tipo: 'warn' });
    else if (i.resultado === 'RECHAZADA') pasos.push({ fecha: i.fecha, texto: `${envio}: rechazada${i.motivo ? ' — ' + i.motivo : ''}`, tipo: 'danger' });
    else pasos.push({ fecha: i.fecha, texto: `${envio}: el servidor no respondió (${i.codigo}); se reintentará`, tipo: 'warn' });
  }
  const huboConflicto = intentos.some((i) => i.resultado === 'EN_CONFLICTO');
  if (huboConflicto && o.estado === 'CONFIRMADA') pasos.push({ fecha: null, texto: 'Resuelta por el Encargado: reintentada y confirmada', tipo: 'ok' });
  else if (huboConflicto && o.estado === 'RECHAZADA') pasos.push({ fecha: null, texto: 'Resuelta por el Encargado: descartada', tipo: 'danger' });
  else if (o.estado === 'REGISTRADA_LOCAL' || o.estado === 'ENVIADA') pasos.push({ fecha: null, texto: o.estado === 'ENVIADA' ? 'Esperando la respuesta del servidor…' : 'Pendiente: se enviará sola al volver la conexión', tipo: 'info' });
  return pasos;
}
