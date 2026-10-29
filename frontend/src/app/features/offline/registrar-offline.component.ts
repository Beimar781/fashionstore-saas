import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../core/auth/auth.service';
import { CatalogoLocalService, PrendaLocal } from '../../core/offline/catalogo-local.service';
import { ColaOperacionesService } from '../../core/offline/cola-operaciones.service';
import { ConnectivityService } from '../../core/offline/connectivity.service';
import { ToastService } from '../../core/ui/toast.service';

interface Linea { variante_id: number; texto: string; precio: number; cantidad: number; max: number; }

/** RF19 · Registrar sin conexión: el personal registra ventas de contado (RN13) y el cliente reserva. Todo usa el catálogo guardado y queda en la cola para sincronizar. */
@Component({
  selector: 'app-registrar-offline',
  imports: [FormsModule],
  template: `
    <section class="card pad stack">
      <h2>{{ !esCliente ? 'Venta de contado sin conexión' : modo === 'COMPRA' ? 'Comprar sin conexión' : 'Reservar sin conexión' }}</h2>
      @if (esCliente) {
        <div class="row"><label style="max-width:240px">¿Qué desea hacer?<select name="modo" [(ngModel)]="modo"><option value="RESERVA">Reservar para probarme</option><option value="COMPRA">Comprar (pago con tarjeta al sincronizar)</option></select></label></div>
      }
      <p class="small muted">{{ esCliente ? (modo === 'COMPRA' ? 'La compra queda registrada en el dispositivo. Al recuperar la conexión verificamos que la prenda siga disponible y le avisamos para que la pague con tarjeta en «Mis compras»; no se cobra nada sin conexión.' : 'La reserva se confirma cuando el dispositivo recupere la conexión.') : 'Las ventas sin conexión son de contado. Recibir el efectivo aquí no significa que el servidor ya la aceptó: se confirma al sincronizar.' }}</p>
      @if (!local.hayCatalogo()) { <div class="alert warn" role="status">Primero descargue el catálogo (pestaña «Catálogo»).</div> }
      @else {
        @if (esCliente) {
          <div class="row">
            <label style="min-width:220px">Sucursal<select name="s" [(ngModel)]="sucursalId">@for (s of local.meta()?.sucursales ?? []; track s.id) { <option [ngValue]="s.id">{{ s.nombre }} · {{ s.ciudad }}</option> }</select></label>
            @if (modo === 'RESERVA') { <label>Fecha y hora de visita<input name="f" type="datetime-local" [(ngModel)]="visita" /></label> }
          </div>
        }
        <label>Buscar prenda<input name="q" [ngModel]="texto()" (ngModelChange)="texto.set($event)" placeholder="Nombre, SKU o código de barras" autocomplete="off" /></label>
        @if (texto().trim()) {
          <div class="row" style="flex-wrap:wrap">
            @for (r of resultados(); track r.variante.id) { <button type="button" class="chip" [disabled]="stock(r) === 0" (click)="agregar(r)">{{ r.producto.nombre }} · {{ r.variante.talla }} · {{ r.variante.color }} · Bs {{ r.variante.precio_final }} ({{ stock(r) }})</button> }
          </div>
        }
        @for (l of lineas(); track l.variante_id) {
          <div class="row between small"><span>{{ l.texto }} · Bs {{ l.precio }}</span>
            <span class="row"><input type="number" min="1" [max]="l.max" [name]="'c' + l.variante_id" [(ngModel)]="l.cantidad" style="width:4.5rem" (ngModelChange)="lineas.set([...lineas()])" /><button type="button" class="btn sm danger" (click)="quitar(l)">✕</button></span></div>
        }
        @if (lineas().length) {
          <div class="row between total"><strong>Total</strong><strong>Bs {{ total().toFixed(2) }}</strong></div>
          @if (esCliente && modo === 'RESERVA') { <label>Notas (opcional)<input name="n" [(ngModel)]="notas" maxlength="300" /></label> }
          @else if (esCliente) { <div class="alert warn" role="status">Si cuando sincronice la prenda ya se agotó, le avisaremos y no se le cobrará nada.</div> }
          @else {
            <div class="row">
              <label style="max-width:200px">Efectivo recibido (Bs)<input name="r" type="number" min="0" step="0.01" [(ngModel)]="recibido" /></label>
              <div class="cambio" [class.mal]="cambio() < 0"><span class="small muted">Cambio a entregar</span><strong>Bs {{ cambio() < 0 ? '—' : cambio().toFixed(2) }}</strong></div>
              <label style="min-width:240px">Cliente (opcional)<select name="cl" [(ngModel)]="clienteEmail"><option [ngValue]="null">Consumidor final</option>@for (c of local.meta()?.clientes ?? []; track c.id) { <option [ngValue]="c.email">{{ c.nombre }} · {{ c.email }}</option> }</select></label>
            </div>
          }
          @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          <div><button class="btn primary" (click)="registrar()" [disabled]="guardando()">{{ !esCliente ? 'Registrar venta en el dispositivo' : modo === 'COMPRA' ? 'Registrar compra en el dispositivo' : 'Registrar reserva en el dispositivo' }}</button></div>
        }
      }
    </section>`,
  styles: `.total { border-top: 1px solid var(--line); padding-top: .6rem; } .cambio { display: grid; } .cambio.mal strong { color: var(--danger); }
    .chip { border: 1px solid var(--line); background: var(--surface); border-radius: 999px; padding: .25rem .7rem; font-size: .82rem; cursor: pointer; } .chip:disabled { opacity: .5; cursor: not-allowed; }`,
})
export class RegistrarOfflineComponent {
  readonly local = inject(CatalogoLocalService);
  private cola = inject(ColaOperacionesService);
  readonly red = inject(ConnectivityService);
  private auth = inject(AuthService);
  private toast = inject(ToastService);

  readonly esCliente = this.auth.rol() === 'Cliente';
  readonly texto = signal('');
  readonly lineas = signal<Linea[]>([]);
  readonly error = signal('');
  readonly guardando = signal(false);
  sucursalId: number | null = this.auth.sesion()?.usuario.sucursal_id ?? this.local.meta()?.sucursales[0]?.id ?? null;
  modo: 'RESERVA' | 'COMPRA' = 'RESERVA';
  visita = '';
  notas = '';
  recibido: number | null = null;
  clienteEmail: string | null = null;

  readonly resultados = computed(() => this.local.buscar(this.texto()));
  readonly total = computed(() => this.lineas().reduce((t, l) => t + l.precio * l.cantidad, 0));
  readonly cambio = () => (this.recibido ?? 0) - this.total();

  stock(r: PrendaLocal) { return this.local.stock(r.variante, this.sucursalId); }

  agregar(r: PrendaLocal) {
    const existente = this.lineas().find((l) => l.variante_id === r.variante.id);
    if (existente) { if (existente.cantidad < existente.max) existente.cantidad++; this.lineas.set([...this.lineas()]); return; }
    this.lineas.update((l) => [...l, { variante_id: r.variante.id, texto: `${r.producto.nombre} (${r.variante.talla}, ${r.variante.color})`, precio: Number(r.variante.precio_final), cantidad: 1, max: this.stock(r) }]);
  }
  quitar(l: Linea) { this.lineas.update((x) => x.filter((y) => y !== l)); }

  async registrar() {
    this.error.set('');
    if (this.sucursalId === null) { this.error.set('Elija una sucursal.'); return; }
    const items = this.lineas().map((l) => ({ variante_id: l.variante_id, cantidad: l.cantidad }));
    const resumen = this.lineas().map((l) => `${l.cantidad}× ${l.texto}`).join(', ');
    if (this.esCliente && this.modo === 'COMPRA') {
      this.guardando.set(true);
      await this.cola.registrar('COMPRA', { sucursal_id: this.sucursalId, items }, this.sucursalId, `Compra: ${resumen}`);
    } else if (this.esCliente) {
      if (!this.visita) { this.error.set('Indique la fecha y hora de su visita.'); return; }
      this.guardando.set(true);
      await this.cola.registrar('RESERVA', { sucursal_id: this.sucursalId, programada_para: this.visita, notas: this.notas, items }, this.sucursalId, `Reserva: ${resumen}`);
    } else {
      if ((this.recibido ?? -1) < this.total()) { this.error.set('El efectivo recibido es menor al total de la venta.'); return; }
      this.guardando.set(true);
      await this.cola.registrar('VENTA_CONTADO', { items, monto_recibido: (this.recibido ?? 0).toFixed(2), cliente_email: this.clienteEmail }, this.sucursalId, `Venta de contado Bs ${this.total().toFixed(2)}: ${resumen}`);
    }
    await this.local.comprometer(items, this.sucursalId);
    this.toast.ok(this.red.online() ? 'Operación registrada; se está sincronizando.' : 'Operación guardada en este dispositivo. Se sincronizará al recuperar la conexión.');
    this.lineas.set([]); this.recibido = null; this.notas = ''; this.texto.set(''); this.guardando.set(false);
  }
}
