import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { OfflineApi } from '../../core/api/offline.api';
import { OperacionServidor } from '../../core/offline.models';
import { ToastService, mensajeError } from '../../core/ui/toast.service';

/** CU-40 · Conflictos de sincronización: operaciones hechas sin conexión que no se pudieron aplicar por falta de existencias. Nada se descontó (RN14): el Encargado reintenta o descarta. */
@Component({
  selector: 'app-conflictos',
  imports: [FormsModule, DatePipe],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Conflictos de sincronización</h1><p>Ventas, compras y reservas hechas sin conexión que no alcanzaron en el inventario. No se descontó nada del stock.</p></div><button class="btn" (click)="cargar()">Actualizar</button></div>
      @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
      @for (c of conflictos(); track c.id) {
        <section class="card pad stack" style="margin-bottom:1rem">
          <div class="row between">
            <div><strong>{{ c.tipo === 'VENTA_CONTADO' ? 'Venta de contado' : c.tipo === 'COMPRA' ? 'Compra del cliente' : 'Reserva' }}</strong> · {{ c.sucursal }} · registrada por {{ c.usuario }} el {{ c.creada_en | date: 'dd/MM/yyyy HH:mm' }}</div>
            <span class="badge warn">En conflicto · {{ c.intentos }} intento(s)</span>
          </div>
          <p class="small">{{ c.mensaje }}</p>
          <div class="table-wrap"><table>
            <thead><tr><th>Prenda</th><th class="right">Solicitadas</th><th class="right">Disponibles hoy</th></tr></thead>
            <tbody>@for (f of c.detalle?.faltantes ?? []; track f.variante_id) { <tr><td>{{ f.producto }} ({{ f.talla }}, {{ f.color }})</td><td class="right">{{ f.solicitadas }}</td><td class="right"><strong>{{ f.disponibles }}</strong></td></tr> }</tbody>
          </table></div>
          @if (descartando() === c.id) {
            <label>Motivo del descarte<input name="m{{ c.id }}" [(ngModel)]="motivo" maxlength="200" placeholder="Por ejemplo: el cliente ya se fue" /></label>
            @if (c.tipo === 'VENTA_CONTADO') {
              <label class="check"><input type="checkbox" name="dv{{ c.id }}" [(ngModel)]="devolverDinero" /> Devolver el efectivo al cliente (registra la devolución y la nota; la prenda se revisa)</label>
              @if (devolverDinero) {
                <fieldset class="stack" style="border:1px solid var(--line);border-radius:8px;padding:.6rem .8rem">
                  <legend class="small"><strong>Revisión de la prenda que vuelve</strong></legend>
                  <label class="check"><input type="checkbox" name="cd{{ c.id }}" [(ngModel)]="condicion.sin_danos" /> Sin daños</label>
                  <label class="check"><input type="checkbox" name="cg{{ c.id }}" [(ngModel)]="condicion.sin_desgaste" /> Sin desgaste ni señales de uso</label>
                  <label class="check"><input type="checkbox" name="ce{{ c.id }}" [(ngModel)]="condicion.con_etiquetas" /> Conserva sus etiquetas</label>
                </fieldset>
              }
            }
            <div class="row"><button class="btn danger" (click)="descartar(c)" [disabled]="devolverDinero && !condicionCompleta()">{{ devolverDinero ? 'Descartar y devolver el dinero' : 'Confirmar descarte' }}</button><button class="btn ghost" (click)="descartando.set(null)">Cancelar</button></div>
          } @else {
            <div class="row">
              <button class="btn primary" (click)="reintentar(c)" [disabled]="trabajando()">Reintentar con las existencias de ahora</button>
              <button class="btn ghost" (click)="descartando.set(c.id); motivo = ''; devolverDinero = false; condicion = { sin_danos: false, sin_desgaste: false, con_etiquetas: false }">Descartar…</button>
            </div>
            <p class="small muted">Si llegó mercadería, recíbala primero en «Recepción de mercadería» y luego reintente. Al descartar una venta de contado, puede devolver el efectivo desde aquí o hacerlo a mano.</p>
          }
        </section>
      } @empty { <div class="card empty">No hay operaciones en conflicto.</div> }
    </div>`,
})
export class ConflictosPage implements OnInit {
  private api = inject(OfflineApi);
  private toast = inject(ToastService);

  readonly conflictos = signal<OperacionServidor[]>([]);
  readonly error = signal('');
  readonly descartando = signal<string | null>(null);
  readonly trabajando = signal(false);
  motivo = '';
  devolverDinero = false;
  condicion = { sin_danos: false, sin_desgaste: false, con_etiquetas: false };
  condicionCompleta() { const c = this.condicion; return c.sin_danos && c.sin_desgaste && c.con_etiquetas; }

  ngOnInit() { this.cargar(); }

  cargar() { this.error.set(''); this.api.conflictos().subscribe({ next: (l) => this.conflictos.set(l), error: (e) => this.error.set(mensajeError(e)) }); }

  reintentar(c: OperacionServidor) {
    this.trabajando.set(true);
    this.api.resolver(c.id, 'REINTENTAR').subscribe({
      next: (o) => { this.trabajando.set(false); this.toast.ok(`Operación confirmada${o.referencia ? ' (' + o.referencia + ')' : ''}.`); this.cargar(); },
      error: (e) => { this.trabajando.set(false); this.toast.error(mensajeError(e)); this.cargar(); },
    });
  }

  descartar(c: OperacionServidor) {
    this.api.resolver(c.id, 'DESCARTAR', this.motivo, this.devolverDinero ? { ...this.condicion } : undefined).subscribe({
      next: (o) => { this.descartando.set(null); this.toast.ok(this.devolverDinero ? 'Operación descartada y dinero devuelto.' : 'Operación descartada.'); void o; this.cargar(); },
      error: (e) => this.toast.error(mensajeError(e)),
    });
  }
}
