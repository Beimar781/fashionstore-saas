import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { InventarioApi } from '../../core/api/inventario.api';
import { Lote } from '../../core/inventario.models';
import { ToastService, mensajeError } from '../../core/ui/toast.service';

/** Recepción de lotes en tránsito (CU-31 → CU-26): al recibir se cuentan las unidades y se suman al inventario de la sucursal. */
@Component({
  selector: 'app-recepciones',
  imports: [FormsModule],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Recepción de mercadería</h1><p>Lotes que los proveedores despacharon y todavía no se suman al inventario.</p></div></div>
      @if (cargando()) { <div class="empty">Cargando…</div> }
      @else if (!lotes().length) { <div class="card empty">No hay lotes en tránsito.</div> }
      @else {
        <div class="stack">
          @for (l of lotes(); track l.id) {
            <section class="card pad stack">
              <div class="row between">
                <div><h3>{{ l.codigo }} <span class="badge warn">En tránsito</span></h3><p class="muted small">{{ l.proveedor }} → {{ l.sucursal }} · {{ l.referencia || 'sin referencia' }} · {{ l.creado_en.slice(0, 10) }}</p></div>
                <button class="btn primary" (click)="abrir(l)">Recibir</button>
              </div>
              <div class="table-wrap"><table>
                <thead><tr><th>Producto</th><th>Talla</th><th>Color</th><th>SKU</th><th class="right">Despachadas</th></tr></thead>
                <tbody>@for (i of l.items; track i.id) { <tr><td>{{ i.producto }}</td><td>{{ i.talla }}</td><td>{{ i.color }}</td><td>{{ i.sku }}</td><td class="right">{{ i.cantidad }}</td></tr> }</tbody>
              </table></div>
            </section>
          }
        </div>
      }
    </div>

    @if (lote(); as l) {
      <div class="overlay" (click)="lote.set(null)">
        <form class="modal" (click)="$event.stopPropagation()" (ngSubmit)="confirmar()" role="dialog" aria-modal="true">
          <header><h2>Recibir {{ l.codigo }}</h2><button type="button" class="btn sm ghost" (click)="lote.set(null)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <p class="muted small">Cuente lo que llegó. Si falta algo, corrija la cantidad: solo se suma lo recibido.</p>
            <div class="table-wrap"><table>
              <thead><tr><th>Producto</th><th class="right">Despachadas</th><th class="right">Recibidas</th></tr></thead>
              <tbody>@for (i of l.items; track i.id) { <tr><td>{{ i.producto }} · {{ i.talla }} · {{ i.color }}</td><td class="right">{{ i.cantidad }}</td>
                <td><input type="number" min="0" [max]="i.cantidad" [(ngModel)]="recibidas[i.id]" [name]="'r' + i.id" style="width:6rem;margin-left:auto;display:block" /></td></tr> }</tbody>
            </table></div>
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          </div>
          <footer><button type="button" class="btn" (click)="lote.set(null)">Cancelar</button><button class="btn primary" [disabled]="guardando()">Confirmar recepción</button></footer>
        </form>
      </div>
    }`,
})
export class RecepcionesPage implements OnInit {
  private api = inject(InventarioApi);
  private toast = inject(ToastService);

  readonly lotes = signal<Lote[]>([]);
  readonly lote = signal<Lote | null>(null);
  readonly cargando = signal(true);
  readonly guardando = signal(false);
  readonly error = signal('');
  recibidas: Record<number, number> = {};

  ngOnInit() { this.cargar(); }

  cargar() {
    this.api.recepciones().subscribe({
      next: (r) => { this.lotes.set(r); this.cargando.set(false); },
      error: (e) => { this.cargando.set(false); this.toast.error(mensajeError(e)); },
    });
  }

  abrir(l: Lote) { this.recibidas = Object.fromEntries(l.items.map((i) => [i.id, i.cantidad])); this.error.set(''); this.lote.set(l); }

  confirmar() {
    const l = this.lote()!;
    this.guardando.set(true); this.error.set('');
    this.api.recibir(l.id, l.items.map((i) => ({ item_id: i.id, cantidad_recibida: Number(this.recibidas[i.id] ?? 0) }))).subscribe({
      next: () => { this.guardando.set(false); this.lote.set(null); this.toast.ok(`Lote ${l.codigo} recibido: el inventario se actualizó.`); this.cargar(); },
      error: (e) => { this.guardando.set(false); this.error.set(mensajeError(e)); },
    });
  }
}
