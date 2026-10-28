import { Injectable, computed, effect, inject, signal, untracked } from '@angular/core';
import { AuthService } from '../auth/auth.service';
import { PrendaElegida } from '../reservas.models';

/** Prendas que el cliente va juntando para reservar. Se guardan en el navegador, separadas por usuario. */
@Injectable({ providedIn: 'root' })
export class ReservaBorradorService {
  private auth = inject(AuthService);
  readonly prendas = signal<PrendaElegida[]>([]);
  readonly total = computed(() => this.prendas().reduce((suma, p) => suma + p.cantidad, 0));

  constructor() {
    // al cambiar de usuario (otra sesión en el mismo navegador) se carga SU borrador
    effect(() => { this.auth.sesion(); untracked(() => this.prendas.set(this.leer())); });
  }

  agregar(p: Omit<PrendaElegida, 'cantidad'>) {
    const lista = [...this.prendas()];
    const existente = lista.find((x) => x.variante_id === p.variante_id);
    if (existente) existente.cantidad = Math.min(existente.cantidad + 1, 10, p.max);
    else lista.push({ ...p, cantidad: 1 });
    this.guardar(lista);
  }

  cambiarCantidad(varianteId: number, cantidad: number) {
    this.guardar(this.prendas().map((p) => (p.variante_id === varianteId ? { ...p, cantidad: Math.max(1, Math.min(cantidad, 10)) } : p)));
  }

  quitar(varianteId: number) { this.guardar(this.prendas().filter((p) => p.variante_id !== varianteId)); }
  vaciar() { this.guardar([]); }

  private clave() { return `fs.reserva.${this.auth.sesion()?.usuario.id ?? 0}`; }
  private guardar(lista: PrendaElegida[]) {
    this.prendas.set(lista);
    try { localStorage.setItem(this.clave(), JSON.stringify(lista)); } catch { /* sin almacenamiento: queda solo en memoria */ }
  }
  private leer(): PrendaElegida[] {
    try { return JSON.parse(localStorage.getItem(this.clave()) ?? '[]'); } catch { return []; }
  }
}
