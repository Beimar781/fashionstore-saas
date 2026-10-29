import { Injectable, inject } from '@angular/core';
import { ReportesApi } from '../api/reportes.api';
import { AuthService } from '../auth/auth.service';
import { ROL } from '../models';

/** CU-07 · Avisa al sistema lo que el cliente busca y mira, para que aprenda sus gustos. Solo si el plan incluye IA; si falla o el cliente apagó la personalización, no pasa nada. */
@Injectable({ providedIn: 'root' })
export class AprendizajeService {
  private api = inject(ReportesApi);
  private auth = inject(AuthService);

  private activo() { return this.auth.rol() === ROL.CLIENTE && !!this.auth.sesion()?.suscripcion?.plan?.reportes_ia; }

  busqueda(f: { q?: string | null; categoria_id?: number | null; color_id?: number | null; talla?: string | null; precio_max?: number | null }) {
    const texto = f.q?.trim() || null;
    if (!this.activo() || !(texto || f.categoria_id || f.color_id || f.talla || f.precio_max)) return;
    this.api.interaccion({ tipo: 'BUSQUEDA', texto, categoria_id: f.categoria_id ?? null, color_id: f.color_id ?? null, talla: f.talla || null, precio_max: f.precio_max ?? null }).subscribe({ error: () => undefined });
  }

  vista(productoId: number) {
    if (!this.activo() || !productoId) return;
    this.api.interaccion({ tipo: 'VISTA', producto_id: productoId }).subscribe({ error: () => undefined });
  }
}
