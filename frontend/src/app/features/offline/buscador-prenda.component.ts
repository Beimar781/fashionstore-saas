import { Component, computed, inject, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CatalogoLocalService, PrendaLocal } from '../../core/offline/catalogo-local.service';
import { EscanerComponent, hayEscaner } from '../../core/ui/escaner.component';

/** Busca una prenda en la copia descargada por nombre, SKU o código de barras (también escaneando con la cámara, B7). Emite la prenda elegida. */
@Component({
  selector: 'app-buscador-prenda',
  imports: [FormsModule, EscanerComponent],
  template: `
    @if (!elegida()) {
      <div class="row"><label style="flex:1">Buscar por nombre, SKU o código de barras<input name="bq" [ngModel]="texto()" (ngModelChange)="texto.set($event)" autocomplete="off" /></label>
        @if (conEscaner) { <button type="button" class="btn" style="align-self:end" (click)="escaneando.set(true)">Escanear</button> }</div>
      <div class="row" style="flex-wrap:wrap">@for (r of resultados(); track r.variante.id) { <button type="button" class="chip" (click)="elegir(r)">{{ r.producto.nombre }} · {{ r.variante.talla }} · {{ r.variante.color }}</button> }</div>
    } @else {
      <div class="row between"><span>{{ elegida()!.producto.nombre }} · {{ elegida()!.variante.talla }} · {{ elegida()!.variante.color }}</span><button type="button" class="btn sm ghost" (click)="limpiar()">Cambiar</button></div>
    }
    @if (escaneando()) { <app-escaner (codigo)="alEscanear($event)" (cerrar)="escaneando.set(false)" /> }`,
  styles: `.chip { border: 1px solid var(--line); background: var(--surface); border-radius: 999px; padding: .25rem .7rem; font-size: .82rem; cursor: pointer; }`,
})
export class BuscadorPrendaComponent {
  private local = inject(CatalogoLocalService);

  readonly prenda = output<PrendaLocal | null>();
  readonly conEscaner = hayEscaner();
  readonly texto = signal('');
  readonly elegida = signal<PrendaLocal | null>(null);
  readonly escaneando = signal(false);
  readonly resultados = computed(() => (this.texto().trim() ? this.local.buscar(this.texto()).slice(0, 12) : []));

  elegir(r: PrendaLocal) { this.elegida.set(r); this.prenda.emit(r); }
  limpiar() { this.elegida.set(null); this.texto.set(''); this.prenda.emit(null); }

  alEscanear(codigo: string) {
    this.escaneando.set(false);
    this.texto.set(codigo);
    const r = this.local.buscar(codigo);
    if (r.length === 1) this.elegir(r[0]);
  }
}
