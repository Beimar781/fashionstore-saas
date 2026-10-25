import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AdministracionApi } from '../../core/api/administracion.api';
import { Ciudad, Sucursal, UsoPlan } from '../../core/models';
import { ToastService, mensajeError } from '../../core/ui/toast.service';

/** CU-14 · Gestionar ciudades y sucursales dentro del límite del plan (RN06). */
@Component({
  selector: 'app-sucursales',
  imports: [FormsModule],
  template: `
    <div class="page">
      <div class="page-head">
        <div><h1>Ciudades y sucursales</h1><p>Las sucursales activas cuentan para el límite de su plan.</p></div>
        <button class="btn primary" (click)="abrirNueva()" [disabled]="sinCupo()" [title]="sinCupo() ? 'Límite del plan alcanzado' : ''">+ Nueva sucursal</button>
      </div>

      @if (uso(); as u) {
        <section class="card pad stack" style="margin-bottom:1rem">
          <div class="row between">
            <strong>{{ u.activas }} de {{ u.limite }} sucursales activas <span class="muted small">· plan {{ u.plan }}</span></strong>
            @if (sinCupo()) { <span class="badge danger">Límite alcanzado</span> }
          </div>
          <div class="meter" [class.full]="sinCupo()"><span [style.width.%]="(u.activas / (u.limite || 1)) * 100"></span></div>
          @if (sinCupo()) { <p class="small muted">Desactive una sucursal o solicite el cambio de plan para crear nuevas.</p> }
        </section>
      }

      <div class="card table-wrap">
        @if (cargando()) { <div class="empty">Cargando…</div> }
        @else if (!sucursales().length) { <div class="empty">Aún no registró sucursales.</div> }
        @else {
          <table>
            <thead><tr><th>Sucursal</th><th>Ciudad</th><th>Dirección</th><th>Teléfono</th><th>Horario</th><th>Estado</th><th></th></tr></thead>
            <tbody>
              @for (s of sucursales(); track s.id) {
                <tr>
                  <td><strong>{{ s.nombre }}</strong></td><td>{{ s.ciudad }}</td><td>{{ s.direccion ?? '—' }}</td><td>{{ s.telefono ?? '—' }}</td><td>{{ s.horario ?? '—' }}</td>
                  <td><span class="badge" [class.ok]="s.activa" [class.warn]="!s.activa">{{ s.activa ? 'Activa' : 'Inactiva' }}</span></td>
                  <td class="actions">
                    <button class="btn sm" (click)="abrirEditar(s)">Editar</button>
                    @if (s.activa) { <button class="btn sm danger" (click)="desactivar(s)">Desactivar</button> }
                    @else { <button class="btn sm" (click)="activar(s)">Activar</button> }
                  </td>
                </tr>
              }
            </tbody>
          </table>
        }
      </div>
    </div>

    @if (modal()) {
      <div class="overlay" (click)="modal.set(false)">
        <form class="modal" (click)="$event.stopPropagation()" (ngSubmit)="guardar()" #f="ngForm" role="dialog" aria-modal="true">
          <header><h2>{{ editandoId ? 'Editar sucursal' : 'Nueva sucursal' }}</h2><button type="button" class="btn sm ghost" (click)="modal.set(false)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <div class="form-grid">
              <label class="full">Nombre<input name="n" [(ngModel)]="form.nombre" required /></label>
              <label>Ciudad
                <select name="c" [(ngModel)]="form.ciudad_id" (ngModelChange)="form.ciudad_nombre = ''">
                  <option [ngValue]="null">{{ editandoId ? 'Seleccione…' : 'Otra (escribir abajo)' }}</option>
                  @for (c of ciudades(); track c.id) { <option [ngValue]="c.id">{{ c.nombre }}</option> }
                </select></label>
              @if (!editandoId && form.ciudad_id === null) {
                <label>Nueva ciudad<input name="cn" [(ngModel)]="form.ciudad_nombre" required placeholder="Cochabamba" /></label>
              }
              <label class="full">Dirección<input name="d" [(ngModel)]="form.direccion" /></label>
              <label>Teléfono<input name="t" [(ngModel)]="form.telefono" /></label>
              <label>Horario<input name="h" [(ngModel)]="form.horario" placeholder="Lun-Sáb 9:00-20:00" /></label>
            </div>
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          </div>
          <footer><button type="button" class="btn" (click)="modal.set(false)">Cancelar</button><button class="btn primary" [disabled]="guardando() || !f.valid">Guardar</button></footer>
        </form>
      </div>
    }`,
})
export class SucursalesPage implements OnInit {
  private api = inject(AdministracionApi);
  private toast = inject(ToastService);

  readonly sucursales = signal<Sucursal[]>([]);
  readonly ciudades = signal<Ciudad[]>([]);
  readonly uso = signal<UsoPlan | null>(null);
  readonly sinCupo = computed(() => { const u = this.uso(); return !!u && u.limite !== null && u.activas >= u.limite; });
  readonly cargando = signal(true);
  readonly modal = signal(false);
  readonly guardando = signal(false);
  readonly error = signal('');
  editandoId = 0;
  form = this.vacio();

  ngOnInit() { this.cargar(); }

  cargar() {
    this.api.sucursales().subscribe({
      next: (r) => { this.sucursales.set(r.sucursales); this.uso.set(r.uso_plan); this.cargando.set(false); },
      error: (e) => { this.cargando.set(false); this.toast.error(mensajeError(e)); },
    });
    this.api.ciudades().subscribe((c) => this.ciudades.set(c));
  }

  abrirNueva() { this.editandoId = 0; this.form = this.vacio(); this.form.ciudad_id = this.ciudades()[0]?.id ?? null; this.error.set(''); this.modal.set(true); }
  abrirEditar(s: Sucursal) {
    this.editandoId = s.id; this.error.set('');
    this.form = { nombre: s.nombre, ciudad_id: s.ciudad_id, ciudad_nombre: '', direccion: s.direccion ?? '', telefono: s.telefono ?? '', horario: s.horario ?? '' };
    this.modal.set(true);
  }

  guardar() {
    this.guardando.set(true); this.error.set('');
    const f = this.form;
    const op = this.editandoId
      ? this.api.editarSucursal(this.editandoId, { nombre: f.nombre, ciudad_id: f.ciudad_id, direccion: f.direccion || null, telefono: f.telefono || null, horario: f.horario || null })
      : this.api.crearSucursal({ nombre: f.nombre, ciudad_id: f.ciudad_id, ciudad_nombre: f.ciudad_id === null ? f.ciudad_nombre : null, direccion: f.direccion || null, telefono: f.telefono || null, horario: f.horario || null });
    op.subscribe({
      next: () => { this.guardando.set(false); this.modal.set(false); this.toast.ok('Sucursal guardada.'); this.cargar(); },
      error: (e) => { this.guardando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  activar(s: Sucursal) { this.api.activarSucursal(s.id).subscribe({ next: () => { this.toast.ok('Sucursal activada.'); this.cargar(); }, error: (e) => this.toast.error(mensajeError(e)) }); }
  desactivar(s: Sucursal) {
    if (!confirm(`¿Desactivar la sucursal ${s.nombre}?`)) return;
    this.api.desactivarSucursal(s.id).subscribe({ next: () => { this.toast.ok('Sucursal desactivada.'); this.cargar(); }, error: (e) => this.toast.error(mensajeError(e)) });
  }

  private vacio() { return { nombre: '', ciudad_id: null as number | null, ciudad_nombre: '', direccion: '', telefono: '', horario: '' }; }
}
