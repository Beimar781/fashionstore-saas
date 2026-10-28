import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../core/auth/auth.service';
import { CatalogoApi } from '../../core/api/catalogo.api';
import { InventarioApi } from '../../core/api/inventario.api';
import { MovimientosPagina, TIPOS_MOVIMIENTO } from '../../core/inventario.models';
import { ROL } from '../../core/models';
import { ToastService, mensajeError } from '../../core/ui/toast.service';

/** Bitácora de movimientos de inventario: tipo, referencia y usuario de cada cambio. El Encargado ve su sucursal; el Administrador, todas. */
@Component({
  selector: 'app-movimientos',
  imports: [FormsModule],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Movimientos de inventario</h1><p>Todo cambio de existencias queda registrado y no se puede editar.</p></div></div>
      <form class="card pad row" style="margin-bottom:1rem" (ngSubmit)="irA(1)">
        @if (!esEncargado) { <select name="s" [(ngModel)]="f.sucursal" style="width:auto"><option [ngValue]="null">Todas las sucursales</option>@for (s of sucursales(); track s.id) { <option [ngValue]="s.id">{{ s.nombre }}</option> }</select> }
        <select name="t" [(ngModel)]="f.tipo" style="width:auto"><option value="">Todos los tipos</option>@for (t of tipos; track t[0]) { <option [value]="t[0]">{{ t[1] }}</option> }</select>
        <label class="row" style="gap:.4rem">Desde<input name="d" type="date" [(ngModel)]="f.desde" style="width:auto" /></label>
        <label class="row" style="gap:.4rem">Hasta<input name="h" type="date" [(ngModel)]="f.hasta" style="width:auto" /></label>
        <button class="btn">Filtrar</button>
      </form>
      <div class="card table-wrap">
        @if (cargando()) { <div class="empty">Cargando…</div> }
        @else if (!datos()?.items?.length) { <div class="empty">No hay movimientos.</div> }
        @else {
          <table>
            <thead><tr><th>Fecha</th><th>Sucursal</th><th>Producto</th><th>Movimiento</th><th class="right">Cant.</th><th>Referencia</th><th>Usuario</th><th>Nota</th></tr></thead>
            <tbody>
              @for (m of datos()!.items; track m.id) {
                <tr>
                  <td class="nowrap small">{{ m.creado_en.slice(0, 16).replace('T', ' ') }}</td><td>{{ m.sucursal }}</td>
                  <td><strong>{{ m.producto }}</strong><div class="muted small">{{ m.talla }} · {{ m.color }} · {{ m.sku }}</div></td>
                  <td><span class="badge" [class.ok]="entra(m.tipo)" [class.warn]="!entra(m.tipo)">{{ nombreTipo(m.tipo) }}</span></td>
                  <td class="right"><strong>{{ entra(m.tipo) ? '+' : '−' }}{{ m.cantidad }}</strong></td>
                  <td class="small">{{ m.referencia_tipo }}{{ m.referencia_id ? ' #' + m.referencia_id : '' }}</td><td>{{ m.usuario ?? '—' }}</td><td class="small">{{ m.nota }}</td>
                </tr>
              }
            </tbody>
          </table>
          <div class="row between" style="padding:.7rem 1rem">
            <span class="muted small">{{ datos()!.total }} movimientos · página {{ datos()!.pagina }} de {{ paginas() }}</span>
            <div class="row"><button class="btn sm" [disabled]="datos()!.pagina <= 1" (click)="irA(datos()!.pagina - 1)">Anterior</button><button class="btn sm" [disabled]="datos()!.pagina >= paginas()" (click)="irA(datos()!.pagina + 1)">Siguiente</button></div>
          </div>
        }
      </div>
    </div>`,
})
export class MovimientosPage implements OnInit {
  private api = inject(InventarioApi);
  private publico = inject(CatalogoApi);
  private toast = inject(ToastService);
  readonly esEncargado = inject(AuthService).rol() === ROL.ENCARGADO;

  readonly tipos = Object.entries(TIPOS_MOVIMIENTO);
  readonly datos = signal<MovimientosPagina | null>(null);
  readonly paginas = computed(() => Math.max(1, Math.ceil((this.datos()?.total ?? 0) / (this.datos()?.tamano ?? 25))));
  readonly sucursales = signal<{ id: number; nombre: string }[]>([]);
  readonly cargando = signal(true);
  f = { sucursal: null as number | null, tipo: '', desde: '', hasta: '' };

  ngOnInit() {
    if (!this.esEncargado) this.publico.sucursales().subscribe((r) => this.sucursales.set(r));
    this.irA(1);
  }

  nombreTipo(t: string) { return TIPOS_MOVIMIENTO[t] ?? t; }
  entra(tipo: string) { return ['ENTRADA_RECEPCION', 'AJUSTE_ENTRADA', 'LIBERA_RESERVA', 'DEVOLUCION'].includes(tipo); }

  irA(pagina: number) {
    this.cargando.set(true);
    this.api.movimientos({ ...this.f, pagina }).subscribe({
      next: (r) => { this.datos.set(r); this.cargando.set(false); },
      error: (e) => { this.cargando.set(false); this.toast.error(mensajeError(e)); },
    });
  }
}
