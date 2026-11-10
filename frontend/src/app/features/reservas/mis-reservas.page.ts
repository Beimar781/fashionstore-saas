import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ReservasApi } from '../../core/api/reservas.api';
import { CLASE_ESTADO_RESERVA, EstadoReserva, Reserva, TEXTO_ESTADO_ITEM, TEXTO_ESTADO_RESERVA } from '../../core/reservas.models';
import { ToastService, mensajeError } from '../../core/ui/toast.service';
import { OperacionesConProblemaComponent } from '../offline/operaciones-con-problema.component';
import { ConnectivityService } from '../../core/offline/connectivity.service';
import { ColaOperacionesService } from '../../core/offline/cola-operaciones.service';
import { LocalDbService } from '../../core/offline/local-db.service';
import { AuthService } from '../../core/auth/auth.service';
import { CatalogoLocalService } from '../../core/offline/catalogo-local.service';

type ReservaLista = Omit<Reserva, 'id'> & { id: number | string; pendiente_local?: boolean; estadoLocal?: string };

/** CU-10 · Consultar el estado de las reservas y cancelarlas (RF12). */
@Component({
  selector: 'app-mis-reservas',
  imports: [FormsModule, RouterLink, DatePipe, OperacionesConProblemaComponent],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Mis reservas</h1><p>Presente el código en el mostrador de la sucursal.</p></div><a class="btn primary" routerLink="/tienda/catalogo">+ Nueva reserva</a></div>

      <app-operaciones-con-problema [tipos]="['RESERVA', 'CANCELAR_RESERVA']" titulo="Reservas que no se pudieron realizar" [paraCliente]="true" />

      <div class="tabs" role="tablist">
        @for (f of filtros; track f.valor) { <button role="tab" [class.activa]="estado() === f.valor" (click)="filtrar(f.valor)">{{ f.texto }}</button> }
      </div>

      @if (cargando()) { <div class="empty">Cargando…</div> }
      @else if (!reservas().length) { <div class="card empty">No tiene reservas {{ estado() ? 'con ese estado' : 'todavía' }}.</div> }
      @else {
        <div class="stack">
          @for (r of reservas(); track r.id) {
            <section class="card pad stack">
              <div class="row between">
                <div><span class="codigo">{{ r.codigo }}</span> @if (r.pendiente_local) { <span class="badge warn">Pendiente de sincronizar · {{ r.estadoLocal }}</span> } @else { <span class="badge" [class]="clase(r.estado)">{{ texto(r.estado) }}</span> }
                  <p class="muted small">{{ r.sucursal }} · {{ r.programada_para | date: 'dd/MM/yyyy HH:mm' }} · {{ r.total_unidades }} prenda(s)</p></div>
                @if (r.puede_cancelar) { <button class="btn danger sm" (click)="pedirCancelar(r)">Cancelar reserva</button> }
              </div>
              <ul class="items">
                @for (i of r.items; track i.id) {
                  <li>{{ i.cantidad }} × {{ i.producto }} · {{ i.talla }} · {{ i.color }}
                    @if (i.estado !== 'RESERVADO') { <span class="badge" [class.danger]="i.estado === 'NO_ENCONTRADO'">{{ itemTexto(i.estado) }}</span> }</li>
                }
              </ul>
              @if (r.estado === 'PREPARADA') { <div class="alert ok">Sus prendas están preparadas: puede pasar a la tienda.</div> }
              @if (r.estado === 'PENDIENTE') { <p class="small muted">Vence el {{ r.vence_en | date: 'dd/MM/yyyy HH:mm' }} si no se presenta.</p> }
              @if (r.notas) { <p class="small muted">{{ r.notas }}</p> }
            </section>
          }
        </div>
      }
    </div>

    @if (cancelando(); as r) {
      <div class="overlay" (click)="cancelando.set(null)">
        <form class="modal" (click)="$event.stopPropagation()" (ngSubmit)="cancelar()" role="dialog" aria-modal="true">
          <header><h2>Cancelar {{ r.codigo }}</h2><button type="button" class="btn sm ghost" (click)="cancelando.set(null)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <p>Las prendas volverán a estar disponibles para otros clientes.</p>
            <label>Motivo <span class="hint">(opcional)</span><input name="m" [(ngModel)]="motivo" maxlength="200" /></label>
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          </div>
          <footer><button type="button" class="btn" (click)="cancelando.set(null)">Volver</button><button class="btn danger" [disabled]="enviando()">Sí, cancelar</button></footer>
        </form>
      </div>
    }`,
  styles: `.codigo { font: 700 1.2rem ui-monospace, Consolas, monospace; letter-spacing: .05em; margin-right: .5rem; } .items { margin: 0; padding-left: 1.1rem; display: grid; gap: .25rem; }`,
})
export class MisReservasPage implements OnInit {
  private api = inject(ReservasApi);
  private toast = inject(ToastService);
  private db = inject(LocalDbService);
  private auth = inject(AuthService);
  private cola = inject(ColaOperacionesService);
  private red = inject(ConnectivityService);
  private catalogoLocal = inject(CatalogoLocalService);

  readonly filtros: { valor: string; texto: string }[] = [
    { valor: '', texto: 'Todas' }, { valor: 'PENDIENTE', texto: 'Pendientes' }, { valor: 'PREPARADA', texto: 'Preparadas' },
    { valor: 'COMPLETADA', texto: 'Completadas' }, { valor: 'CANCELADA', texto: 'Canceladas' }, { valor: 'EXPIRADA', texto: 'Expiradas' },
  ];
  readonly reservas = signal<ReservaLista[]>([]);
  readonly estado = signal('');
  readonly cargando = signal(true);
  readonly cancelando = signal<ReservaLista | null>(null);
  readonly enviando = signal(false);
  readonly error = signal('');
  motivo = '';
  readonly texto = (e: EstadoReserva) => TEXTO_ESTADO_RESERVA[e];
  readonly clase = (e: EstadoReserva) => CLASE_ESTADO_RESERVA[e];
  readonly itemTexto = (e: string) => TEXTO_ESTADO_ITEM[e] ?? e;

  constructor() { this.cola.alRefrescar(() => void this.cargar()); }  // tras sincronizar o al volver la red, la lista se actualiza sola

  async ngOnInit() { await this.cola.cargar(); await this.cargar(); }

  filtrar(valor: string) { this.estado.set(valor); this.cargar(); }

  async cargar() {
    this.cargando.set(true);
    const s = this.auth.sesion();
    const clave = `${s?.empresa?.id ?? 0}:${s?.usuario.id ?? 0}`;
    const cache = await this.db.leerReservasClienteLocal<Reserva[]>(clave);
    if (!this.red.online()) { this.reservas.set(this.conPendientes(cache ?? [])); this.cargando.set(false); return; }
    this.api.misReservas(this.estado()).subscribe({
      next: (r) => { if (!this.estado() && s) void this.db.guardarReservasClienteLocal(clave, r); this.reservas.set(this.conPendientes(r)); this.cargando.set(false); },
      error: (e) => { this.reservas.set(this.conPendientes(cache ?? [])); this.cargando.set(false); if (!cache?.length) this.toast.error(mensajeError(e)); },
    });
  }

  private conPendientes(vistas: Reserva[]): ReservaLista[] {
    const meta = this.catalogoLocal.meta();
    const locales = this.cola.operaciones().filter((o) => o.tipo === 'RESERVA' && ['REGISTRADA_LOCAL', 'ENVIADA'].includes(o.estado)).map((o) => {
      const items = (o.payload['items'] as { variante_id: number; cantidad: number }[] | undefined) ?? [];
      return { id: o.id as unknown as number, codigo: o.referencia ?? `RES-${o.id.slice(0, 8).toUpperCase()}`, estado: 'PENDIENTE', estadoLocal: o.estado, pendiente_local: true, sucursal_id: o.sucursal_id ?? 0, sucursal: meta?.sucursales.find((x) => x.id === o.sucursal_id)?.nombre ?? 'Sucursal', cliente_id: 0, cliente: '', programada_para: String(o.payload['programada_para'] ?? o.creada_en), vence_en: '', notas: String(o.payload['notas'] ?? o.resumen), creada_en: o.creada_en, total_unidades: items.reduce((s, i) => s + i.cantidad, 0), puede_cancelar: true, items: items.map((i, n) => { const v = this.catalogoLocal.productos().flatMap((p) => p.variantes).find((x) => x.id === i.variante_id); return { id: n, variante_id: i.variante_id, sku: v?.sku ?? '', producto: this.catalogoLocal.productos().find((p) => p.variantes.some((x) => x.id === i.variante_id))?.nombre ?? 'Prenda', talla: v?.talla ?? '', color: v?.color ?? '', cantidad: i.cantidad, estado: 'RESERVADO' }; }) } as unknown as Reserva;
    }) as ReservaLista[];
    const cancelaciones = this.cola.operaciones().filter((o) => o.tipo === 'CANCELAR_RESERVA' && ['REGISTRADA_LOCAL', 'ENVIADA'].includes(o.estado));
    const vistasConEstado = vistas.map((r) => cancelaciones.some((o) => o.payload['reserva_id'] === r.id) ? { ...r, pendiente_local: true, estadoLocal: 'Cancelación pendiente', puede_cancelar: false } : r);
    return [...locales, ...vistasConEstado];
  }

  pedirCancelar(r: ReservaLista) { this.motivo = ''; this.error.set(''); this.cancelando.set(r); }

  cancelar() {
    const r = this.cancelando()!;
    this.enviando.set(true); this.error.set('');
    if (r.pendiente_local) {
      const operacion = this.cola.operaciones().find((o) => o.id === String(r.id) && o.tipo === 'RESERVA');
      if (operacion) void this.db.borrarOperacion(operacion.id).then(() => this.cola.cargar()).then(() => { this.enviando.set(false); this.cancelando.set(null); this.toast.ok('Reserva local cancelada.'); void this.cargar(); });
      return;
    }
    if (!this.red.online()) {
      void this.cola.registrar('CANCELAR_RESERVA', { reserva_id: r.id, motivo: this.motivo }, r.sucursal_id, `Cancelar reserva ${r.codigo}`).then(() => { this.enviando.set(false); this.cancelando.set(null); this.toast.ok('Cancelación guardada. Se enviará al recuperar la conexión.'); void this.cargar(); }).catch((e) => { this.enviando.set(false); this.error.set(mensajeError(e)); });
      return;
    }
    this.api.cancelar(r.id as number, this.motivo).subscribe({
      next: () => { this.enviando.set(false); this.cancelando.set(null); this.toast.ok(`Reserva ${r.codigo} cancelada.`); this.cargar(); },
      error: (e) => { if (e.status === 0) void this.cola.registrar('CANCELAR_RESERVA', { reserva_id: r.id, motivo: this.motivo }, r.sucursal_id, `Cancelar reserva ${r.codigo}`).then(() => { this.enviando.set(false); this.cancelando.set(null); void this.cargar(); }); else { this.enviando.set(false); this.error.set(mensajeError(e)); } },
    });
  }
}
