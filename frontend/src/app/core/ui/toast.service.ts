import { Injectable, signal } from '@angular/core';

export const MSG_SIN_CONEXION = 'Sin conexión con el servidor.';

export interface AccionToast { texto: string; ruta: string; }
export interface Toast { id: number; tipo: 'ok' | 'danger' | 'warn'; texto: string; accion?: AccionToast; }

@Injectable({ providedIn: 'root' })
export class ToastService {
  readonly toasts = signal<Toast[]>([]);
  private n = 0;

  ok(texto: string) { this.mostrar('ok', texto); }
  /** «Sin conexión» no es un fallo del sistema: se muestra como aviso (ámbar) y no como error rojo duplicado con el mensaje de la pantalla. */
  error(texto: string) { this.mostrar(texto === MSG_SIN_CONEXION ? 'warn' : 'danger', texto, 6000); }
  aviso(texto: string) { this.mostrar('warn', texto, 7000); }

  /** Aviso con un botón que lleva a otra pantalla (por ejemplo «Ver detalle» de la sincronización). */
  mostrarAviso(tipo: Toast['tipo'], texto: string, accion?: AccionToast) { this.mostrar(tipo, texto, accion ? 12000 : 6000, accion); }
  cerrar(id: number) { this.toasts.update((t) => t.filter((x) => x.id !== id)); }

  private mostrar(tipo: Toast['tipo'], texto: string, ms = 3500, accion?: AccionToast) {
    const id = ++this.n;
    this.toasts.update((t) => [...t, { id, tipo, texto, accion }]);
    setTimeout(() => this.toasts.update((t) => t.filter((x) => x.id !== id)), ms);
  }
}

/** Extrae el mensaje controlado del backend ({"detail": "..."}). */
export function mensajeError(err: unknown): string {
  const e = err as { status?: number; error?: { detail?: unknown } };
  if (e?.status === 0) return MSG_SIN_CONEXION;
  const d = e?.error?.detail;
  return typeof d === 'string' ? d : 'No se pudo completar la operación.';
}
