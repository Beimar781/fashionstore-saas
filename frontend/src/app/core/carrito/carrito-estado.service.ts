import { Injectable, effect, inject, signal, untracked } from '@angular/core';
import { ComprasApi } from '../api/compras.api';
import { AuthService } from '../auth/auth.service';
import { Carrito } from '../compras.models';
import { ROL } from '../models';

/** Cuántas prendas hay en el carrito y de qué sucursal (alimenta el menú y el botón «Agregar al carrito»). */
@Injectable({ providedIn: 'root' })
export class CarritoEstadoService {
  private api = inject(ComprasApi);
  private auth = inject(AuthService);
  readonly total = signal(0);
  readonly sucursalId = signal<number | null>(null);
  readonly sucursal = signal<string | null>(null);

  constructor() {
    effect(() => {
      const esCliente = this.auth.rol() === ROL.CLIENTE;
      untracked(() => (esCliente ? this.refrescar() : this.fijar(null)));
    });
  }

  refrescar() { this.api.carrito().subscribe({ next: (c) => this.fijar(c), error: () => {} }); }

  fijar(c: Carrito | null) {
    this.total.set(c?.total_unidades ?? 0);
    this.sucursalId.set(c?.sucursal_id ?? null);
    this.sucursal.set(c?.sucursal ?? null);
  }
}
