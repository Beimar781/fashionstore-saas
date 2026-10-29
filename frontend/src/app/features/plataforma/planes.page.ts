import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { PlataformaApi } from '../../core/api/plataforma.api';
import { Plan } from '../../core/models';
import { ToastService, mensajeError } from '../../core/ui/toast.service';

/** CU-34 · Gestionar planes de suscripción. */
@Component({
  selector: 'app-planes',
  imports: [FormsModule],
  template: `
    <div class="page">
      <div class="page-head">
        <div><h1>Planes de suscripción</h1><p>Los límites y funcionalidades se configuran aquí y se aplican a todas las empresas con el plan.</p></div>
        <button class="btn primary" (click)="abrirNuevo()">+ Nuevo plan</button>
      </div>

      @if (cargando()) { <div class="empty">Cargando…</div> }
      <div class="grid cols-3">
        @for (p of planes(); track p.id) {
          <article class="card pad plan" [class.inactivo]="!p.activo">
            <div class="row between"><h2>{{ p.nombre }}@if (p.es_prueba) { <span class="badge ok" title="Un mes, una sola vez por empresa">Prueba</span> }</h2>
              @if (!p.activo) { <span class="badge warn">Inactivo</span> } @else { <span class="badge accent">{{ p.empresas_suscritas }} {{ p.empresas_suscritas === 1 ? 'empresa' : 'empresas' }}</span> }
            </div>
            <p class="precio">Bs {{ p.precio }}<small> / {{ p.periodicidad === 'anual' ? 'año' : 'mes' }}</small></p>
            <p class="muted small">{{ p.descripcion }}</p>
            <ul>
              <li><strong>Hasta {{ p.max_sucursales }}</strong> sucursales activas</li>
              <li [class.no]="!p.reportes_convencionales">Reportes convencionales</li>
              <li [class.no]="!p.offline">Operación offline</li>
              <li [class.no]="!p.reportes_ia">Reportes generativos con IA</li>
            </ul>
            <div class="row">
              <button class="btn sm" (click)="abrirEditar(p)">Editar</button>
              @if (p.activo) { <button class="btn sm danger" (click)="inactivar(p)">Inactivar</button> }
            </div>
          </article>
        }
      </div>
    </div>

    @if (modal()) {
      <div class="overlay" (click)="modal.set(false)">
        <form class="modal" (click)="$event.stopPropagation()" (ngSubmit)="guardar()" #f="ngForm" role="dialog" aria-modal="true">
          <header><h2>{{ editandoId ? 'Editar plan' : 'Nuevo plan' }}</h2><button type="button" class="btn sm ghost" (click)="modal.set(false)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <div class="form-grid">
              <label>Nombre<input name="n" [(ngModel)]="form.nombre" required /></label>
              <label>Precio referencial (Bs)<input name="pr" type="number" min="0" step="0.01" [(ngModel)]="form.precio" required /></label>
              <label>Periodicidad<select name="pe" [(ngModel)]="form.periodicidad"><option value="mensual">Mensual</option><option value="anual">Anual</option></select></label>
              <label>Límite de sucursales activas<input name="ms" type="number" [(ngModel)]="form.max_sucursales" required /></label>
              <label class="full">Descripción<textarea name="d" rows="2" [(ngModel)]="form.descripcion"></textarea></label>
            </div>
            <fieldset><legend>Funcionalidades habilitadas</legend>
              <div class="stack">
                <label class="check"><input type="checkbox" name="rc" [(ngModel)]="form.reportes_convencionales" /> Reportes convencionales</label>
                <label class="check"><input type="checkbox" name="of" [(ngModel)]="form.offline" /> Operación offline y sincronización</label>
                <label class="check"><input type="checkbox" name="prueba" [(ngModel)]="form.es_prueba" /> Plan de prueba gratuita (dura 1 mes y cada empresa lo usa una sola vez)</label>
                <label class="check"><input type="checkbox" name="ia" [(ngModel)]="form.reportes_ia" /> Reportes generativos con IA y analítica ML</label>
              </div>
            </fieldset>
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          </div>
          <footer><button type="button" class="btn" (click)="modal.set(false)">Cancelar</button><button class="btn primary" [disabled]="guardando() || !f.valid">Guardar</button></footer>
        </form>
      </div>
    }`,
  styles: `
    .plan { display: grid; gap: .7rem; align-content: start; } .plan.inactivo { opacity: .65; }
    .precio { font: 600 1.8rem var(--serif); } .precio small { font: 400 .85rem system-ui; color: var(--muted); }
    ul { list-style: none; padding: 0; margin: 0; display: grid; gap: .35rem; }
    li::before { content: '✓'; color: var(--ok); font-weight: 700; margin-right: .5rem; }
    li.no { color: var(--muted); text-decoration: line-through; } li.no::before { content: '✕'; color: var(--danger); }`,
})
export class PlanesPage implements OnInit {
  private api = inject(PlataformaApi);
  private toast = inject(ToastService);

  readonly planes = signal<Plan[]>([]);
  readonly cargando = signal(true);
  readonly modal = signal(false);
  readonly guardando = signal(false);
  readonly error = signal('');
  editandoId = 0;
  form = this.vacio();

  ngOnInit() { this.cargar(); }
  cargar() { this.api.planes().subscribe({ next: (p) => { this.planes.set(p); this.cargando.set(false); }, error: (e) => { this.cargando.set(false); this.toast.error(mensajeError(e)); } }); }

  abrirNuevo() { this.editandoId = 0; this.form = this.vacio(); this.error.set(''); this.modal.set(true); }
  abrirEditar(p: Plan) {
    this.editandoId = p.id; this.error.set('');
    this.form = { nombre: p.nombre, descripcion: p.descripcion ?? '', precio: Number(p.precio), periodicidad: p.periodicidad, max_sucursales: p.max_sucursales,
      reportes_ia: p.reportes_ia, offline: p.offline, reportes_convencionales: p.reportes_convencionales, es_prueba: p.es_prueba };
    this.modal.set(true);
  }

  guardar() {
    this.guardando.set(true); this.error.set('');
    const op = this.editandoId ? this.api.modificarPlan(this.editandoId, this.form) : this.api.crearPlan(this.form);
    op.subscribe({
      next: (r) => {
        this.guardando.set(false); this.modal.set(false); this.toast.ok('Plan guardado.'); this.cargar();
        if (r.advertencias.length) {
          this.toast.aviso('Empresas por encima del nuevo límite: ' + r.advertencias.map((a) => `${a.codigo} (${a.sucursales_activas}/${a.limite})`).join(', ') + '. No se desactivaron sucursales.');
        }
      },
      error: (e) => { this.guardando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  inactivar(p: Plan) {
    if (!confirm(`¿Inactivar el plan ${p.nombre}? Dejará de ofrecerse a nuevas contrataciones; las suscripciones vigentes se mantienen.`)) return;
    this.api.inactivarPlan(p.id).subscribe({ next: () => { this.toast.ok('Plan inactivado.'); this.cargar(); }, error: (e) => this.toast.error(mensajeError(e)) });
  }

  private vacio() {
    return { nombre: '', descripcion: '', precio: 0, periodicidad: 'mensual', max_sucursales: 2, reportes_ia: false, offline: true, reportes_convencionales: true, es_prueba: false };
  }
}
