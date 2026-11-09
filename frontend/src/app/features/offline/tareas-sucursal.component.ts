import { DatePipe, NgTemplateOutlet } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../core/auth/auth.service';
import { CatalogoLocalService, PrendaLocal } from '../../core/offline/catalogo-local.service';
import { ColaOperacionesService } from '../../core/offline/cola-operaciones.service';
import { ReservaSucursalLocal, VentaReciente } from '../../core/offline.models';
import { EscanerComponent, hayEscaner } from '../../core/ui/escaner.component';
import { ToastService } from '../../core/ui/toast.service';
import { BsPipe } from '../../core/formato-bs';

export const MSG_PLAZO_VENCIDO = 'El plazo de devolución de esta venta venció.';
type Tarea = 'devolucion' | 'recepcion' | 'ajuste' | 'reservas';

/** B3 a B6 · Tareas de la sucursal sin conexión. El Cajero devuelve prendas; el Encargado, además, recibe mercadería, ajusta el inventario y atiende reservas.
 *  Cada tarea queda en la cola con su UUID y se envía sola al recuperar la red; el servidor vuelve a validar todo al sincronizar. */
@Component({
  selector: 'app-tareas-sucursal',
  imports: [BsPipe, FormsModule, DatePipe, EscanerComponent, NgTemplateOutlet],
  template: `
    <section class="card pad stack">
      <div class="tabs" role="tablist">
        <button role="tab" [class.activa]="tarea() === 'devolucion'" (click)="tarea.set('devolucion')">Devolución</button>
        @if (encargado) {
          <button role="tab" [class.activa]="tarea() === 'recepcion'" (click)="tarea.set('recepcion')">Recepción</button>
          <button role="tab" [class.activa]="tarea() === 'ajuste'" (click)="tarea.set('ajuste')">Ajuste de inventario</button>
          <button role="tab" [class.activa]="tarea() === 'reservas'" (click)="tarea.set('reservas')">Reservas</button>
        }
      </div>
      @if (!local.meta()) { <div class="alert warn" role="status">Primero descargue el catálogo con conexión (pestaña «Catálogo»).</div> }
      @else {
      @switch (tarea()) {
        @case ('devolucion') {
          @if (!venta()) {
            <p class="small muted">Ventas recientes de la sucursal, dentro del plazo de devolución, descargadas con el catálogo.</p>
            <label>Buscar por número de comprobante<input name="cb" [ngModel]="filtro()" (ngModelChange)="filtro.set($event)" autocomplete="off" /></label>
            @for (v of ventasVisibles(); track v.comprobante) { <button type="button" class="btn" (click)="elegirVenta(v)">{{ v.comprobante }} · {{ v.total | bs }} · {{ v.pagado_en | date: 'dd/MM HH:mm' }}</button> }
            @empty { <p class="muted small">No hay ventas descargadas.</p> }
          } @else {
            <h3>Venta {{ venta()!.comprobante }}</h3>
            <p class="small muted">Plazo hasta {{ venta()!.vence_el | date: 'dd/MM/yyyy HH:mm' }}</p>
            @for (i of venta()!.items; track i.pedido_item_id) {
              <div class="row between small"><span>{{ i.producto }} ({{ i.talla }}, {{ i.color }}) · vendidas {{ i.vendida }} · se pueden devolver {{ i.devolvible }}</span>
                <input type="number" min="0" [max]="i.devolvible" [ngModel]="cantidades()[i.pedido_item_id] || 0" (ngModelChange)="poner(i.pedido_item_id, $event, i.devolvible)" [name]="'c' + i.pedido_item_id" style="width:5rem" /></div>
            }
            <label>Motivo<input name="mo" [(ngModel)]="motivo" maxlength="200" /></label>
            <label class="check"><input type="checkbox" name="sd" [(ngModel)]="condicion.sin_danos" /> Sin daños</label>
            <label class="check"><input type="checkbox" name="sg" [(ngModel)]="condicion.sin_desgaste" /> Sin desgaste</label>
            <label class="check"><input type="checkbox" name="ce" [(ngModel)]="condicion.con_etiquetas" /> Con sus etiquetas</label>
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
            <div class="row"><button class="btn" (click)="venta.set(null)">Volver</button><button class="btn primary" (click)="registrarDevolucion()">Registrar devolución</button></div>
          }
        }
        @case ('recepcion') {
          <p class="small muted">La mercadería recibida sube el inventario de forma provisional hasta sincronizar.</p>
          <ng-container *ngTemplateOutlet="buscador" />
          <label>Cantidad recibida<input type="number" min="1" name="qr" [(ngModel)]="cantidad" /></label>
          <label>Referencia del envío o proveedor<input name="rf" [(ngModel)]="referencia" maxlength="100" /></label>
          @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          <button class="btn primary" (click)="registrarRecepcion()">Registrar recepción</button>
        }
        @case ('ajuste') {
          <p class="small muted">El ajuste se envía como diferencia (no como valor absoluto) para no pisar las ventas hechas mientras tanto. Si dejaría el stock negativo, queda en conflicto.</p>
          <ng-container *ngTemplateOutlet="buscador" />
          <label>Diferencia (por ejemplo +3 o -2)<input type="number" name="df" [(ngModel)]="diferencia" /></label>
          <label>Motivo (obligatorio)<select name="mt" [(ngModel)]="motivoAjuste"><option value="CONTEO">Conteo físico</option><option value="MERMA">Merma</option><option value="DAÑO">Daño</option></select></label>
          <label>Nota (opcional)<input name="nt" [(ngModel)]="nota" maxlength="150" /></label>
          @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          <button class="btn primary" (click)="registrarAjuste()">Registrar ajuste</button>
        }
        @case ('reservas') {
          <label>Validar el código de la reserva<input name="cr" [ngModel]="filtro()" (ngModelChange)="filtro.set($event)" autocomplete="off" /></label>
          @for (r of reservasVisibles(); track r.id) {
            <div class="card pad stack">
              <strong>{{ r.codigo }} · {{ r.estado }}</strong><span class="small muted">Visita {{ r.programada_para | date: 'dd/MM HH:mm' }}</span>
              @for (i of r.items; track i.id) {
                <div class="row between small"><span>{{ i.cantidad }}× {{ i.producto }} ({{ i.talla }}, {{ i.color }}) · {{ i.estado }}</span>
                  @if (i.estado === 'RESERVADO' && r.estado !== 'EN_PROBADOR') { <button class="btn sm" (click)="noEncontrada(r, i.id)">No encontrada</button> }</div>
              }
              <div class="row">
                @if (r.estado === 'PENDIENTE') { <button class="btn sm" (click)="preparar(r)">Preparar</button> }
                @if (r.estado === 'PENDIENTE' || r.estado === 'PREPARADA') { <button class="btn sm primary" (click)="atender(r, true)">Atender · lleva las prendas</button><button class="btn sm" (click)="atender(r, false)">Atender · no las lleva</button> }
              </div>
            </div>
          } @empty { <p class="muted small">No hay reservas descargadas con ese código.</p> }
        }
      }
      }
    </section>

    <ng-template #buscador>
      @if (!prenda()) {
        <div class="row"><label style="flex:1">Buscar por nombre, SKU o código de barras<input name="bq" [ngModel]="texto()" (ngModelChange)="texto.set($event)" autocomplete="off" /></label>
          @if (conEscaner) { <button type="button" class="btn" (click)="escaneando.set(true)">Escanear</button> }</div>
        <div class="row" style="flex-wrap:wrap">@for (r of resultados(); track r.variante.id) { <button type="button" class="chip" (click)="prenda.set(r)">{{ r.producto.nombre }} · {{ r.variante.talla }} · {{ r.variante.color }}</button> }</div>
      } @else {
        <div class="row between"><span>{{ prenda()!.producto.nombre }} · {{ prenda()!.variante.talla }} · {{ prenda()!.variante.color }}</span><button type="button" class="btn sm ghost" (click)="prenda.set(null)">Cambiar</button></div>
      }
    </ng-template>
    @if (escaneando()) { <app-escaner (codigo)="alEscanear($event)" (cerrar)="escaneando.set(false)" /> }`,
})
export class TareasSucursalComponent implements OnInit {
  readonly local = inject(CatalogoLocalService);
  private cola = inject(ColaOperacionesService);
  private toast = inject(ToastService);
  private auth = inject(AuthService);

  readonly encargado = this.auth.rol() === 'Encargado';
  readonly conEscaner = hayEscaner();
  readonly tarea = signal<Tarea>('devolucion');
  readonly filtro = signal('');
  readonly venta = signal<VentaReciente | null>(null);
  readonly cantidades = signal<Record<number, number>>({});
  readonly prenda = signal<PrendaLocal | null>(null);
  readonly texto = signal('');
  readonly escaneando = signal(false);
  readonly error = signal('');
  readonly resultados = computed(() => (this.texto().trim() ? this.local.buscar(this.texto()).slice(0, 12) : []));
  readonly ventasVisibles = computed(() => (this.local.meta()?.ventas_recientes ?? []).filter((v) => !this.filtro().trim() || v.comprobante.toLowerCase().includes(this.filtro().trim().toLowerCase())));
  readonly reservasVisibles = computed(() => (this.local.meta()?.reservas_sucursal ?? []).filter((r) => !this.filtro().trim() || r.codigo.toLowerCase().includes(this.filtro().trim().toLowerCase())));
  motivo = ''; condicion = { sin_danos: true, sin_desgaste: true, con_etiquetas: true };
  cantidad = 1; referencia = ''; diferencia: number | null = null; motivoAjuste = 'CONTEO'; nota = '';

  ngOnInit() { void this.local.cargar(); }

  private get sucursalId() { return this.auth.sesion()?.usuario.sucursal_id ?? null; }

  elegirVenta(v: VentaReciente) { this.venta.set(v); this.cantidades.set({}); this.error.set(''); }
  poner(id: number, valor: number, maximo: number) { this.cantidades.update((c) => ({ ...c, [id]: Math.max(0, Math.min(Number(valor) || 0, maximo)) })); }

  alEscanear(codigo: string) { this.escaneando.set(false); this.texto.set(codigo); const r = this.local.buscar(codigo); if (r.length === 1) this.prenda.set(r[0]); }

  /** B3: se valida el plazo guardado en la descarga; el servidor lo vuelve a validar al sincronizar. */
  async registrarDevolucion() {
    const venta = this.venta()!;
    const elegidas = Object.entries(this.cantidades()).filter(([, c]) => c > 0).map(([id, c]) => ({ pedido_item_id: Number(id), cantidad: c }));
    if (new Date() > new Date(venta.vence_el)) { this.error.set(MSG_PLAZO_VENCIDO); return; }
    if (!elegidas.length) { this.error.set('Elija al menos una prenda y su cantidad.'); return; }
    await this.cola.registrar('DEVOLUCION', { comprobante: venta.comprobante, motivo: this.motivo.trim(), items: elegidas, condicion: { ...this.condicion } }, this.sucursalId, `Devolución de ${venta.comprobante}`);
    await this.local.actualizarExtras((m) => { for (const v of m.ventas_recientes ?? []) if (v.comprobante === venta.comprobante) for (const i of v.items) { const c = elegidas.find((e) => e.pedido_item_id === i.pedido_item_id); if (c) i.devolvible = Math.max(i.devolvible - c.cantidad, 0); } });
    this.toast.ok('Devolución guardada. Se enviará sola al recuperar la conexión.');
    this.venta.set(null); this.motivo = ''; this.error.set('');
  }

  async registrarRecepcion() {
    const p = this.prenda();
    if (!p || !(this.cantidad >= 1)) { this.error.set('Elija la prenda e indique una cantidad de 1 o más.'); return; }
    if (!this.referencia.trim()) { this.error.set('Indique la referencia del envío o del proveedor.'); return; }
    await this.cola.registrar('RECEPCION', { variante_id: p.variante.id, cantidad: this.cantidad, referencia: this.referencia.trim() }, this.sucursalId, `Recepción de ${this.cantidad}× ${p.producto.nombre} (${p.variante.talla}, ${p.variante.color})`);
    await this.local.moverStock(p.variante.id, this.sucursalId!, this.cantidad);
    this.toast.ok('Recepción guardada. El inventario sube de forma provisional hasta sincronizar.');
    this.prenda.set(null); this.referencia = ''; this.cantidad = 1; this.error.set('');
  }

  async registrarAjuste() {
    const p = this.prenda();
    if (!p || !this.diferencia) { this.error.set('Elija la prenda e indique la diferencia (positiva o negativa, distinta de cero).'); return; }
    await this.cola.registrar('AJUSTE_INVENTARIO', { variante_id: p.variante.id, diferencia: this.diferencia, motivo: this.motivoAjuste, nota: this.nota.trim() }, this.sucursalId, `Ajuste de ${this.diferencia > 0 ? '+' : ''}${this.diferencia}× ${p.producto.nombre} (${this.motivoAjuste})`);
    await this.local.moverStock(p.variante.id, this.sucursalId!, this.diferencia);
    this.toast.ok('Ajuste guardado. Se enviará como diferencia al recuperar la conexión.');
    this.prenda.set(null); this.diferencia = null; this.nota = ''; this.error.set('');
  }

  private async tareaDeReserva(r: ReservaSucursalLocal, tipo: 'PREPARAR_RESERVA' | 'PRENDA_NO_ENCONTRADA' | 'ATENDER_RESERVA', resumen: string, extra: Record<string, unknown>, cambio: (m: ReservaSucursalLocal[]) => void) {
    await this.cola.registrar(tipo, { reserva_id: r.id, ...extra }, this.sucursalId, `${resumen} ${r.codigo}`);
    await this.local.actualizarExtras((m) => cambio(m.reservas_sucursal ?? []));
  }
  preparar(r: ReservaSucursalLocal) { return this.tareaDeReserva(r, 'PREPARAR_RESERVA', 'Preparación de la reserva', {}, (l) => { for (const x of l) if (x.id === r.id) x.estado = 'PREPARADA'; }); }
  noEncontrada(r: ReservaSucursalLocal, itemId: number) { return this.tareaDeReserva(r, 'PRENDA_NO_ENCONTRADA', 'Prenda no encontrada de la reserva', { item_id: itemId }, (l) => { for (const x of l) if (x.id === r.id) for (const i of x.items) if (i.id === itemId) i.estado = 'NO_ENCONTRADO'; }); }
  async atender(r: ReservaSucursalLocal, lleva: boolean) {
    await this.tareaDeReserva(r, 'ATENDER_RESERVA', 'Atención de la reserva', { llevara_prendas: lleva }, (l) => { if (lleva) { for (const x of l) if (x.id === r.id) x.estado = 'EN_PROBADOR'; } else l.splice(0, l.length, ...l.filter((x) => x.id !== r.id)); });
    this.toast.ok(lleva ? 'Atención guardada. Registre ahora la venta de contado en la pestaña «Registrar».' : 'Atención guardada.');
  }
}
