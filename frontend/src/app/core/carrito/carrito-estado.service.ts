import { Injectable, effect, inject, signal, untracked } from '@angular/core';
import { ivaIncluido } from '../iva';
import { firstValueFrom } from 'rxjs';
import { ComprasApi } from '../api/compras.api';
import { AuthService } from '../auth/auth.service';
import { Carrito } from '../compras.models';
import { ItemCarrito } from '../compras.models';
import { ROL } from '../models';
import { LocalDbService } from '../offline/local-db.service';
import { CatalogoLocalService } from '../offline/catalogo-local.service';
import { ColaOperacionesService } from '../offline/cola-operaciones.service';
import { ToastService } from '../ui/toast.service';
import { ConnectivityService } from '../offline/connectivity.service';

/** Cambios hechos sin conexión sobre prendas que ya estaban en el carrito del servidor; se repiten en orden al volver la red. */
export type EdicionCarrito = { tipo: 'cantidad'; item_id: number; cantidad: number } | { tipo: 'quitar'; item_id: number } | { tipo: 'vaciar' };

/** Cuántas prendas hay en el carrito y de qué sucursal (alimenta el menú y el botón «Agregar al carrito»). */
@Injectable({ providedIn: 'root' })
export class CarritoEstadoService {
  private api = inject(ComprasApi);
  private auth = inject(AuthService);
  private db = inject(LocalDbService);
  private catalogoLocal = inject(CatalogoLocalService);
  private cola = inject(ColaOperacionesService);
  private toast = inject(ToastService);
  private red = inject(ConnectivityService);
  readonly total = signal(0);
  readonly sucursalId = signal<number | null>(null);
  readonly sucursal = signal<string | null>(null);
  readonly carritoLocal = signal<Carrito | null>(null);
  readonly ediciones = signal<EdicionCarrito[]>([]);

  constructor() {
    effect(() => {
      const esCliente = this.auth.rol() === ROL.CLIENTE;
      const enLinea = this.red.online();
      untracked(() => { if (esCliente) { void this.cargarLocal().then(() => { if (enLinea) this.refrescar(); }); } else this.fijar(null); });
    });
  }

  async refrescar() {
    try {
      await this.reenviarEdiciones();
      const c = await new Promise<Carrito>((ok, mal) => this.api.carrito().subscribe({ next: ok, error: mal }));
      this.fijar(c);
      void this.db.guardarCarritoLocal(`espejo:${this.claveLocal()}`, c);  // E1 · copia del carrito del servidor: el checkout la encuentra sin red
      if (this.carritoLocal()?.items.length) await this.fusionarLocal(c);
    } catch { if (this.carritoLocal()?.items.length) this.fijar(this.carritoLocal()); }
  }

  private claveLocal() { const s = this.auth.sesion(); return `${s?.empresa?.id ?? 0}:${s?.usuario.id ?? 0}`; }
  async cargarLocal() { const c = await this.db.leerCarritoLocal<Carrito>(this.claveLocal()); if (c) { this.carritoLocal.set(c); this.fijar(c); } }
  // ---- E2 · el carrito sin conexión: lo último que mostró el servidor + los cambios hechos aquí + las prendas agregadas aquí ----
  private claveEdiciones() { return `ediciones:${this.claveLocal()}`; }
  async cargarEdiciones() { this.ediciones.set((await this.db.leerCarritoLocal<EdicionCarrito[]>(this.claveEdiciones())) ?? []); }
  private async anotar(e: EdicionCarrito | null) {
    const lista = e === null ? [] : [...this.ediciones(), e];
    this.ediciones.set(lista);
    if (lista.length) await this.db.guardarCarritoLocal(this.claveEdiciones(), lista); else await this.db.borrarCarritoLocal(this.claveEdiciones());
  }

  /** El carrito tal como lo ve quien no tiene conexión; null si en este dispositivo nunca se guardó uno. */
  async vistaSinConexion(): Promise<Carrito | null> {
    await this.cargarLocal(); await this.cargarEdiciones();
    const espejo = await this.leerEspejo();
    const local = this.carritoLocal();
    if (!espejo && !local) return null;
    let items: ItemCarrito[] = structuredClone(espejo?.items ?? []);
    for (const e of this.ediciones()) {
      if (e.tipo === 'vaciar') items = [];
      else if (e.tipo === 'quitar') items = items.filter((i) => i.id !== e.item_id);
      else items = items.map((i) => (i.id === e.item_id ? { ...i, cantidad: e.cantidad } : i));
    }
    items.push(...structuredClone(local?.items ?? []));
    return this.calcular(items, (espejo?.sucursal_id ?? local?.sucursal_id)!, espejo?.sucursal ?? local?.sucursal ?? null);
  }

  /** Las prendas agregadas sin conexión tienen id negativo; las del servidor, el de su fila. */
  async cambiarCantidadSinConexion(item: ItemCarrito, cantidad: number) {
    if (!Number.isInteger(cantidad) || cantidad < 1 || cantidad > 10) throw new Error('La cantidad debe estar entre 1 y 10.');
    if (item.disponible !== undefined && cantidad > item.disponible) throw new Error('No hay más unidades disponibles en el catálogo descargado.');
    if (item.id < 0) await this.cambiarLocal(item.id, cantidad);
    else await this.anotar({ tipo: 'cantidad', item_id: item.id, cantidad });
  }

  async quitarSinConexion(item: ItemCarrito) {
    if (item.id < 0) await this.cambiarLocal(item.id, 0);
    else await this.anotar({ tipo: 'quitar', item_id: item.id });
  }

  async vaciarSinConexion() {
    await this.anotar({ tipo: 'vaciar' });
    this.carritoLocal.set(null); await this.db.borrarCarritoLocal(this.claveLocal());
  }

  private async cambiarLocal(id: number, cantidad: number) {
    const local = this.carritoLocal(); if (!local) return;
    const items = local.items.map((i) => (i.id === id ? { ...i, cantidad } : i)).filter((i) => i.cantidad > 0);
    if (!items.length) { this.carritoLocal.set(null); await this.db.borrarCarritoLocal(this.claveLocal()); return; }
    const carrito = this.calcular(items, local.sucursal_id!, local.sucursal);
    this.carritoLocal.set(carrito); await this.db.guardarCarritoLocal(this.claveLocal(), carrito);
  }

  /** Al volver la red se repiten, en orden, los cambios hechos sin conexión sobre el carrito del servidor. Una prenda que ya no se puede se informa; si la red cae a mitad, el resto espera. */
  private async reenviarEdiciones() {
    await this.cargarEdiciones();
    const pendientes = [...this.ediciones()];
    if (!pendientes.length) return;
    let rechazadas = 0;
    for (const [n, e] of pendientes.entries()) {
      try {
        if (e.tipo === 'vaciar') await firstValueFrom(this.api.vaciar());
        else if (e.tipo === 'quitar') await firstValueFrom(this.api.quitar(e.item_id));
        else await firstValueFrom(this.api.cambiarCantidad(e.item_id, e.cantidad));
      } catch (x) {
        if ((x as { status?: number }).status === 0) { this.ediciones.set(pendientes.slice(n)); await this.db.guardarCarritoLocal(this.claveEdiciones(), pendientes.slice(n)); throw x; }
        rechazadas++;
      }
    }
    await this.anotar(null);
    if (rechazadas) this.toast.error(`No se pudieron aplicar ${rechazadas} cambio(s) del carrito hechos sin conexión (la prenda ya no está o no hay stock).`);
  }

  /** Último carrito que mostró el servidor (distinto del local, que son prendas pendientes de fusionar). */
  async leerEspejo() { return this.db.leerCarritoLocal<Carrito>(`espejo:${this.claveLocal()}`); }
  async guardarLocal(carrito: Carrito) { this.carritoLocal.set(carrito); this.fijar(carrito); await this.db.guardarCarritoLocal(this.claveLocal(), carrito); }

  async agregarLocal(varianteId: number, sucursalId: number) {
    if (!this.carritoLocal()) await this.cargarLocal();
    const producto = this.catalogoLocal.productos().find((p) => p.variantes.some((v) => v.id === varianteId));
    const variante = producto?.variantes.find((v) => v.id === varianteId);
    if (!producto || !variante) throw new Error('Descargue el catálogo antes de agregar prendas sin conexión.');
    const disponibles = this.catalogoLocal.stock(variante, sucursalId);
    const actual = this.carritoLocal()?.items.find((i) => i.variante_id === varianteId)?.cantidad ?? 0;
    if (actual >= disponibles) throw new Error('No hay más unidades disponibles en el catálogo descargado.');
    const localActual = this.carritoLocal() as (Carrito & { fusion_id?: string }) | null;
    if (localActual?.fusion_id) throw new Error('Se está sincronizando el carrito. Espere a que termine antes de agregar otra prenda.');
    const items = [...(localActual?.items ?? [])];
    const anterior = items.find((i) => i.variante_id === varianteId);
    if (anterior) anterior.cantidad++;
    else items.push({ id: -varianteId, variante_id: varianteId, producto_id: producto.id, sku: variante.sku, producto: producto.nombre, talla: variante.talla, color: variante.color, imagen: producto.imagen, cantidad: 1, precio: variante.precio, precio_final: variante.precio_final, subtotal: variante.precio_final, disponible: disponibles, estado: 'OK' });
    const sucursal = this.catalogoLocal.meta()?.sucursales.find((s) => s.id === sucursalId);
    const carrito = Object.assign(this.calcular(items, sucursalId, sucursal?.nombre ?? null), { fusion_id: undefined });
    this.carritoLocal.set(carrito); this.fijar(carrito);
    await this.db.guardarCarritoLocal(this.claveLocal(), carrito);
  }

  /** `pago`: si el cliente eligió pagar con una tarjeta GUARDADA, solo viajan su identificador y el total que autorizó; el cobro lo hace el servidor al sincronizar. */
  async registrarCompraLocal(datos: { tipo_entrega: 'DELIVERY' | 'RETIRO'; direccion_entrega: string; nit_ci: string; razon_social: string }, pago?: { tarjeta_guardada_id: number; marca: string; ultimos4: string }, carrito?: Carrito | null) {
    const c = carrito ?? this.carritoLocal();
    if (!c?.items.length || !c.sucursal_id) throw new Error('El carrito local está vacío o no tiene sucursal.');
    await this.cola.registrar('COMPRA', { sucursal_id: c.sucursal_id, tipo_entrega: datos.tipo_entrega, direccion_entrega: datos.direccion_entrega, nit_ci: datos.nit_ci, razon_social: datos.razon_social, items: c.items.map((i) => ({ variante_id: i.variante_id, cantidad: i.cantidad })), ...(pago ? { tarjeta_guardada_id: pago.tarjeta_guardada_id, total_autorizado: Number(c.total).toFixed(2) } : {}) }, c.sucursal_id, `Compra offline: ${c.total_unidades} prenda(s)${pago ? ` · se cobrará a ${pago.marca} terminada en ${pago.ultimos4}` : ''}`);
    await this.db.borrarCarritoLocal(this.claveLocal()); this.carritoLocal.set(null);
    await this.db.borrarCarritoLocal(`espejo:${this.claveLocal()}`); await this.anotar(null);  // la compra ya contiene todo: ni la copia ni los cambios pendientes se repiten
    this.fijar(null);
  }

  private calcular(items: ItemCarrito[], sucursalId: number, sucursal: string | null): Carrito {
    for (const i of items) i.subtotal = (Number(i.precio_final) * i.cantidad).toFixed(2);
    const subtotal = items.reduce((s, i) => s + Number(i.precio) * i.cantidad, 0);
    const total = items.reduce((s, i) => s + Number(i.precio_final) * i.cantidad, 0);
    return { sucursal_id: sucursalId, sucursal, items, total_unidades: items.reduce((s, i) => s + i.cantidad, 0), subtotal: subtotal.toFixed(2), descuento: (subtotal - total).toFixed(2), iva_incluido: ivaIncluido(total.toFixed(2), this.catalogoLocal.meta()?.iva_porcentaje), total: total.toFixed(2), puede_pagar: true, avisos: [] };
  }

  private async fusionarLocal(servidor: Carrito) {
    const local = this.carritoLocal(); if (!local || !servidor.puede_pagar) return;
    // Solo se fusiona cuando el carrito remoto conserva la misma sucursal; el servidor vuelve a validar existencias al agregar.
    if (servidor.sucursal_id !== null && servidor.sucursal_id !== local.sucursal_id) return;
    const guardado = local as Carrito & { fusion_id?: string };
    guardado.fusion_id ??= crypto.randomUUID();
    await this.db.guardarCarritoLocal(this.claveLocal(), guardado);
    let fusion: { carrito: Carrito; rechazadas: { variante_id: number; mensaje: string }[] };
    try { fusion = await new Promise((ok, mal) => this.api.fusionarCarritoLocal({ fusion_id: guardado.fusion_id!, sucursal_id: local.sucursal_id!, items: local.items.map((i) => ({ variante_id: i.variante_id, cantidad: i.cantidad })) }).subscribe({ next: ok, error: mal })); }
    catch { return; }
    if (fusion.rechazadas.length) this.toast.error(`Se quitaron ${fusion.rechazadas.length} prenda(s) que ya no están disponibles: ${fusion.rechazadas.map((x) => x.mensaje).join(' ')}`);
    await this.db.borrarCarritoLocal(this.claveLocal()); this.carritoLocal.set(null);
    this.fijar(fusion.carrito);
  }

  fijar(c: Carrito | null) {
    this.total.set(c?.total_unidades ?? 0);
    this.sucursalId.set(c?.sucursal_id ?? null);
    this.sucursal.set(c?.sucursal ?? null);
  }
}
