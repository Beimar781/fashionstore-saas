import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { CatalogoAdminApi } from '../../../core/api/catalogo-admin.api';
import { Coleccion, TIPOS_TEMPORADA, Temporada } from '../../../core/catalogo.models';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';

type Pestana = 'temporadas' | 'colecciones';

/** CU-17 · Gestionar temporadas y colecciones. Solo el Administrador escribe. */
@Component({
  selector: 'app-temporadas',
  imports: [FormsModule],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Temporadas y colecciones</h1><p>Agrupan los productos por periodo comercial para ordenar el catálogo.</p></div></div>

      <div class="tabs" role="tablist">
        <button role="tab" [class.activa]="pestana() === 'temporadas'" (click)="pestana.set('temporadas')">Temporadas</button>
        <button role="tab" [class.activa]="pestana() === 'colecciones'" (click)="pestana.set('colecciones')">Colecciones</button>
      </div>

      @if (pestana() === 'temporadas') {
        <div class="row between" style="margin-bottom:.8rem"><span class="muted small">{{ temporadas().length }} temporadas</span><button class="btn primary" (click)="nuevaTemporada()">+ Nueva temporada</button></div>
        <div class="card table-wrap">
          @if (!temporadas().length) { <div class="empty">Aún no hay temporadas.</div> } @else {
            <table>
              <thead><tr><th>Temporada</th><th>Código</th><th>Tipo</th><th>Vigencia</th><th>Estado</th><th></th></tr></thead>
              <tbody>
                @for (t of temporadas(); track t.id) {
                  <tr><td><strong>{{ t.nombre }}</strong></td><td>{{ t.codigo }}</td><td>{{ tipoTexto(t.tipo) }}</td><td class="nowrap">{{ t.inicio }} → {{ t.fin }}</td>
                    <td><span class="badge" [class.ok]="t.activa" [class.warn]="!t.activa">{{ t.activa ? 'Activa' : 'Inactiva' }}</span></td>
                    <td class="actions"><button class="btn sm" (click)="editarTemporada(t)">Editar</button> <button class="btn sm danger" (click)="eliminarTemporada(t)">Eliminar</button></td></tr>
                }
              </tbody>
            </table>
          }
        </div>
      } @else {
        <div class="row between" style="margin-bottom:.8rem"><span class="muted small">{{ colecciones().length }} colecciones</span><button class="btn primary" (click)="nuevaColeccion()" [disabled]="!temporadas().length" [title]="temporadas().length ? '' : 'Cree primero una temporada'">+ Nueva colección</button></div>
        <div class="card table-wrap">
          @if (!colecciones().length) { <div class="empty">Aún no hay colecciones.</div> } @else {
            <table>
              <thead><tr><th>Colección</th><th>Temporada</th><th>Lanzamiento</th><th>Estado</th><th></th></tr></thead>
              <tbody>
                @for (c of colecciones(); track c.id) {
                  <tr><td><strong>{{ c.nombre }}</strong></td><td>{{ c.temporada }}</td><td>{{ c.fecha_lanzamiento ?? '—' }}</td>
                    <td><span class="badge" [class.ok]="c.activa" [class.warn]="!c.activa">{{ c.activa ? 'Activa' : 'Inactiva' }}</span></td>
                    <td class="actions"><button class="btn sm" (click)="editarColeccion(c)">Editar</button> <button class="btn sm danger" (click)="eliminarColeccion(c)">Eliminar</button></td></tr>
                }
              </tbody>
            </table>
          }
        </div>
      }
    </div>

    @if (modal()) {
      <div class="overlay" (click)="modal.set(null)">
        <form class="modal" (click)="$event.stopPropagation()" (ngSubmit)="guardar()" #f="ngForm" role="dialog" aria-modal="true">
          <header><h2>{{ titulo() }}</h2><button type="button" class="btn sm ghost" (click)="modal.set(null)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <div class="form-grid">
              @if (modal() === 'temporada') {
                <label class="full">Nombre<input name="n" [(ngModel)]="form.nombre" required minlength="2" placeholder="Primavera-Verano 2026" /></label>
                <label>Código<input name="c" [(ngModel)]="form.codigo" required minlength="2" maxlength="20" placeholder="PV26" /></label>
                <label>Tipo<select name="t" [(ngModel)]="form.tipo">@for (t of tipos; track t.valor) { <option [ngValue]="t.valor">{{ t.texto }}</option> }</select></label>
                <label>Inicio<input name="i" type="date" [(ngModel)]="form.inicio" required /></label>
                <label>Fin<input name="fi" type="date" [(ngModel)]="form.fin" required /></label>
                <label class="check"><input name="a" type="checkbox" [(ngModel)]="form.activa" /> Activa</label>
              } @else {
                <label class="full">Nombre<input name="n" [(ngModel)]="form.nombre" required minlength="2" /></label>
                <label>Temporada<select name="te" [(ngModel)]="form.temporada_id" required>@for (t of temporadas(); track t.id) { <option [ngValue]="t.id">{{ t.nombre }}</option> }</select></label>
                <label>Fecha de lanzamiento<input name="l" type="date" [(ngModel)]="form.fecha_lanzamiento" /></label>
                <label class="check"><input name="a" type="checkbox" [(ngModel)]="form.activa" /> Activa</label>
              }
            </div>
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          </div>
          <footer><button type="button" class="btn" (click)="modal.set(null)">Cancelar</button><button class="btn primary" [disabled]="guardando() || !f.valid">Guardar</button></footer>
        </form>
      </div>
    }`,
})
export class TemporadasPage implements OnInit {
  private api = inject(CatalogoAdminApi);
  private toast = inject(ToastService);

  readonly tipos = TIPOS_TEMPORADA;
  readonly pestana = signal<Pestana>('temporadas');
  readonly temporadas = signal<Temporada[]>([]);
  readonly colecciones = signal<Coleccion[]>([]);
  readonly modal = signal<'temporada' | 'coleccion' | null>(null);
  readonly guardando = signal(false);
  readonly error = signal('');
  editandoId = 0;
  form: any = {};

  readonly titulo = computed(() => `${this.editandoId ? 'Editar' : 'Nueva'} ${this.modal() === 'temporada' ? 'temporada' : 'colección'}`);

  ngOnInit() { this.cargar(); }

  cargar() {
    this.api.temporadas().subscribe((r) => this.temporadas.set(r));
    this.api.colecciones().subscribe((r) => this.colecciones.set(r));
  }

  tipoTexto(valor: string) { return this.tipos.find((t) => t.valor === valor)?.texto ?? valor; }

  private abrir(m: 'temporada' | 'coleccion', id: number, form: object) { this.editandoId = id; this.form = form; this.error.set(''); this.modal.set(m); }
  nuevaTemporada() { this.abrir('temporada', 0, { nombre: '', codigo: '', tipo: 'PRIMAVERA_VERANO', inicio: '', fin: '', activa: true }); }
  editarTemporada(t: Temporada) { this.abrir('temporada', t.id, { nombre: t.nombre, codigo: t.codigo, tipo: t.tipo, inicio: t.inicio, fin: t.fin, activa: t.activa }); }
  nuevaColeccion() { this.abrir('coleccion', 0, { nombre: '', temporada_id: this.temporadas()[0]?.id ?? null, fecha_lanzamiento: null, activa: true }); }
  editarColeccion(c: Coleccion) { this.abrir('coleccion', c.id, { nombre: c.nombre, temporada_id: c.temporada_id, fecha_lanzamiento: c.fecha_lanzamiento, activa: c.activa }); }

  guardar() {
    const f = this.form, id = this.editandoId;
    const peticion: Observable<unknown> = this.modal() === 'temporada'
      ? (id ? this.api.editarTemporada(id, f) : this.api.crearTemporada(f))
      : (id ? this.api.editarColeccion(id, f) : this.api.crearColeccion({ ...f, fecha_lanzamiento: f.fecha_lanzamiento || null }));
    this.guardando.set(true); this.error.set('');
    peticion.subscribe({
      next: () => { this.guardando.set(false); this.modal.set(null); this.toast.ok('Guardado.'); this.cargar(); },
      error: (e) => { this.guardando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  eliminarTemporada(t: Temporada) { this.eliminar(`la temporada ${t.nombre}`, this.api.eliminarTemporada(t.id)); }
  eliminarColeccion(c: Coleccion) { this.eliminar(`la colección ${c.nombre}`, this.api.eliminarColeccion(c.id)); }
  private eliminar(que: string, peticion: ReturnType<CatalogoAdminApi['eliminarMarca']>) {
    if (!confirm(`¿Eliminar ${que}?`)) return;
    peticion.subscribe({ next: () => { this.toast.ok('Eliminado.'); this.cargar(); }, error: (e) => this.toast.error(mensajeError(e)) });
  }
}
