import { Injectable, signal } from '@angular/core';

export interface Toast { id: number; tipo: 'ok' | 'danger' | 'warn'; texto: string; }

@Injectable({ providedIn: 'root' })
export class ToastService {
  readonly toasts = signal<Toast[]>([]);
  private n = 0;

  ok(texto: string) { this.mostrar('ok', texto); }
  error(texto: string) { this.mostrar('danger', texto, 6000); }
  aviso(texto: string) { this.mostrar('warn', texto, 7000); }

  private mostrar(tipo: Toast['tipo'], texto: string, ms = 3500) {
    const id = ++this.n;
    this.toasts.update((t) => [...t, { id, tipo, texto }]);
    setTimeout(() => this.toasts.update((t) => t.filter((x) => x.id !== id)), ms);
  }
}

/** Extrae el mensaje controlado del backend ({"detail": "..."}). */
export function mensajeError(err: unknown): string {
  const e = err as { status?: number; error?: { detail?: unknown } };
  if (e?.status === 0) return 'Sin conexión con el servidor.';
  const d = e?.error?.detail;
  return typeof d === 'string' ? d : 'No se pudo completar la operación.';
}
