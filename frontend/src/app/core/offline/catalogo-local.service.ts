import { Injectable, computed, inject, signal } from '@angular/core';
import { OfflineApi } from '../api/offline.api';
import { MetaCatalogo, ProductoLocal, VarianteLocal } from '../offline.models';
import { LocalDbService } from './local-db.service';

export interface PrendaLocal { producto: ProductoLocal; variante: VarianteLocal; }

/** CU-37 · Catálogo descargado en el dispositivo. Permite consultar y buscar sin conexión; siempre se muestra de cuándo es (RN16). */
@Injectable({ providedIn: 'root' })
export class CatalogoLocalService {
  private api = inject(OfflineApi);
  private db = inject(LocalDbService);

  readonly productos = signal<ProductoLocal[]>([]);
  readonly meta = signal<MetaCatalogo | null>(null);
  readonly descargando = signal(false);
  readonly hayCatalogo = computed(() => this.productos().length > 0);

  constructor() { void this.cargar(); }

  async cargar() {
    this.productos.set(await this.db.leerCatalogo());
    this.meta.set((await this.db.metaCatalogo()) ?? null);
  }

  /** Descarga el subconjunto autorizado del catálogo y lo guarda en IndexedDB. */
  descargar(): Promise<void> {
    this.descargando.set(true);
    return new Promise((resolver, rechazar) => {
      this.api.catalogo().subscribe({
        next: async (c) => {
          const productos: ProductoLocal[] = c.productos.map((p) => ({ ...p, empresa_id: c.empresa_id }));
          const meta: MetaCatalogo = { generado_en: c.generado_en, empresa_id: c.empresa_id, sucursales: c.sucursales, clientes: c.clientes };
          await this.db.guardarCatalogo(productos, meta);
          await this.db.marcarSincronizacion();
          this.productos.set(productos);
          this.meta.set(meta);
          this.descargando.set(false);
          resolver();
        },
        error: (e) => { this.descargando.set(false); rechazar(e); },
      });
    });
  }

  /** Búsqueda local por nombre, categoría, SKU o código de barras. */
  buscar(texto: string): PrendaLocal[] {
    const q = texto.trim().toLowerCase();
    const salida: PrendaLocal[] = [];
    for (const p of this.productos()) {
      const coincideProducto = !q || p.nombre.toLowerCase().includes(q) || p.categoria.toLowerCase().includes(q);
      for (const v of p.variantes) {
        if (coincideProducto || v.sku.toLowerCase().includes(q) || (v.codigo_barras ?? '').toLowerCase() === q) salida.push({ producto: p, variante: v });
      }
    }
    return salida.slice(0, 60);
  }

  stock(v: VarianteLocal, sucursalId: number | null): number {
    if (sucursalId === null) return Object.values(v.stock).reduce((a, b) => a + b, 0);
    return v.stock[String(sucursalId)] ?? 0;
  }

  /** Al registrar una operación sin conexión se descuenta del stock local para no ofrecer lo que ya se comprometió; el servidor vuelve a validar al sincronizar. */
  async comprometer(items: { variante_id: number; cantidad: number }[], sucursalId: number) {
    const cambiados = new Map<number, ProductoLocal>();
    for (const it of items) {
      for (const p of this.productos()) {
        const v = p.variantes.find((x) => x.id === it.variante_id);
        if (v) {
          v.stock[String(sucursalId)] = Math.max((v.stock[String(sucursalId)] ?? 0) - it.cantidad, 0);
          cambiados.set(p.id, p);
        }
      }
    }
    for (const p of cambiados.values()) await this.db.actualizarProducto(p);
    this.productos.update((l) => [...l]);
  }

  async limpiar() { await this.db.borrarCatalogo(); this.productos.set([]); this.meta.set(null); }
}
