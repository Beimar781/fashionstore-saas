import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { CatalogoApi } from '../../core/api/catalogo.api';
import { ReservasApi } from '../../core/api/reservas.api';
import { SucursalCatalogo } from '../../core/catalogo.models';
import { ReservaBorradorService } from '../../core/reservas/reserva-borrador.service';
import { ToastService, mensajeError } from '../../core/ui/toast.service';

/** CU-09 · Reservar varias prendas en una sucursal con un horario aproximado de visita. */
@Component({
  selector: 'app-reservar',
  imports: [FormsModule, RouterLink],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Mi reserva</h1><p>Elija la sucursal y el horario aproximado; allí podrá probarse las prendas y decidir cuáles comprar.</p></div></div>

      @if (!borrador.prendas().length) {
        <div class="card empty">Todavía no eligió prendas. <a routerLink="/tienda/catalogo">Ver el catálogo</a> y use «Agregar a mi reserva».</div>
      } @else {
        <form class="stack" (ngSubmit)="confirmar()" #f="ngForm">
          <section class="card table-wrap">
            <table>
              <thead><tr><th>Prenda</th><th>Talla</th><th>Color</th><th class="right">Cantidad</th><th></th></tr></thead>
              <tbody>
                @for (p of borrador.prendas(); track p.variante_id) {
                  <tr>
                    <td><strong>{{ p.producto }}</strong><div class="muted small">{{ p.sku }}</div></td><td>{{ p.talla }}</td><td>{{ p.color }}</td>
                    <td><input type="number" min="1" max="10" [ngModel]="p.cantidad" (ngModelChange)="borrador.cambiarCantidad(p.variante_id, $event)" [name]="'q' + p.variante_id" style="width:5.5rem;margin-left:auto;display:block" /></td>
                    <td class="actions"><button type="button" class="btn sm danger" (click)="borrador.quitar(p.variante_id)">Quitar</button></td>
                  </tr>
                }
              </tbody>
            </table>
          </section>

          <section class="card pad stack">
            <div class="form-grid">
              <label>Sucursal
                <select name="s" [(ngModel)]="sucursalId" required>
                  @for (s of sucursales(); track s.id) { <option [ngValue]="s.id">{{ s.nombre }} · {{ s.ciudad }}</option> }
                </select></label>
              <label>Día y hora aproximada de su visita
                <input name="h" type="datetime-local" [(ngModel)]="cuando" [min]="minimo" required /></label>
              <label class="full">Notas para la tienda <span class="hint">(opcional)</span><input name="n" [(ngModel)]="notas" maxlength="300" /></label>
            </div>
            @if (sucursalElegida(); as s) { <p class="small muted">{{ s.direccion ?? '' }}{{ s.horario ? ' · Atención: ' + s.horario : '' }}</p> }
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
            <div class="row between">
              <span class="muted small">{{ borrador.total() }} prenda(s) · el stock se aparta de inmediato y la reserva vence 24 horas después del horario elegido.</span>
              <div class="row"><button type="button" class="btn" (click)="borrador.vaciar()">Vaciar</button><button class="btn primary" [disabled]="enviando() || !f.valid">{{ enviando() ? 'Reservando…' : 'Confirmar reserva' }}</button></div>
            </div>
          </section>
        </form>
      }
    </div>`,
})
export class ReservarPage implements OnInit {
  private catalogo = inject(CatalogoApi);
  private api = inject(ReservasApi);
  private toast = inject(ToastService);
  private router = inject(Router);
  readonly borrador = inject(ReservaBorradorService);

  readonly sucursales = signal<SucursalCatalogo[]>([]);
  readonly enviando = signal(false);
  readonly error = signal('');
  readonly sucursalElegida = computed(() => this.sucursales().find((s) => s.id === this.sucursalId) ?? null);
  sucursalId: number | null = null;
  cuando = '';
  notas = '';
  readonly minimo = this.formato(new Date());

  ngOnInit() {
    this.catalogo.sucursales().subscribe((r) => { this.sucursales.set(r); this.sucursalId = r[0]?.id ?? null; });
    const manana = new Date(); manana.setDate(manana.getDate() + 1); manana.setHours(11, 0, 0, 0);
    this.cuando = this.formato(manana);
  }

  confirmar() {
    this.enviando.set(true); this.error.set('');
    const cuerpo = {
      sucursal_id: this.sucursalId, programada_para: this.cuando, notas: this.notas,
      items: this.borrador.prendas().map((p) => ({ variante_id: p.variante_id, cantidad: p.cantidad })),
    };
    this.api.reservar(cuerpo).subscribe({
      next: (r) => { this.enviando.set(false); this.borrador.vaciar(); this.toast.ok(`Reserva ${r.codigo} confirmada. Presente ese código en la tienda.`); void this.router.navigate(['/tienda/reservas']); },
      error: (e) => { this.enviando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  /** Valor para <input type="datetime-local"> en hora local (YYYY-MM-DDTHH:mm). */
  private formato(d: Date) {
    const dos = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}T${dos(d.getHours())}:${dos(d.getMinutes())}`;
  }
}
