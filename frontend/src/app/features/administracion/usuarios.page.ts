import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AdministracionApi } from '../../core/api/administracion.api';
import { Sucursal, Usuario } from '../../core/models';
import { ToastService, mensajeError } from '../../core/ui/toast.service';

/** CU-13 · Gestionar usuarios y roles de la empresa. */
@Component({
  selector: 'app-usuarios',
  imports: [FormsModule, DatePipe],
  template: `
    <div class="page">
      <div class="page-head">
        <div><h1>Usuarios y roles</h1><p>Solo se muestran los usuarios de su empresa.</p></div>
        <button class="btn primary" (click)="abrirNuevo()">+ Nuevo usuario</button>
      </div>
      <div class="card table-wrap">
        @if (cargando()) { <div class="empty">Cargando…</div> }
        @else {
          <table>
            <thead><tr><th>Nombre</th><th>Correo</th><th>Rol</th><th>Sucursal</th><th>Último acceso</th><th>Estado</th><th></th></tr></thead>
            <tbody>
              @for (u of usuarios(); track u.id) {
                <tr>
                  <td><strong>{{ u.nombre }} {{ u.apellidos }}</strong></td><td>{{ u.email }}</td>
                  <td><span class="badge accent">{{ u.rol }}</span></td><td>{{ u.sucursal_nombre ?? '—' }}</td>
                  <td class="muted small nowrap">{{ u.ultimo_acceso ? (u.ultimo_acceso | date: 'dd/MM/yy HH:mm') : 'Nunca' }}</td>
                  <td><span class="badge" [class.ok]="u.activo" [class.danger]="!u.activo">{{ u.activo ? 'Activo' : 'Inactivo' }}</span></td>
                  <td class="actions">
                    <button class="btn sm" (click)="abrirEditar(u)">Editar</button>
                    @if (u.activo) { <button class="btn sm danger" (click)="desactivar(u)">Desactivar</button> }
                    @else { <button class="btn sm" (click)="activar(u)">Activar</button> }
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
          <header><h2>{{ editandoId ? 'Editar usuario' : 'Nuevo usuario' }}</h2><button type="button" class="btn sm ghost" (click)="modal.set(false)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <div class="form-grid">
              <label>Nombre<input name="n" [(ngModel)]="form.nombre" required /></label>
              <label>Apellidos<input name="a" [(ngModel)]="form.apellidos" /></label>
              <label>Correo<input name="e" type="email" [(ngModel)]="form.email" required [disabled]="!!editandoId" /></label>
              <label>{{ editandoId ? 'Nueva contraseña' : 'Contraseña temporal' }} <span class="hint">{{ editandoId ? 'Vacío para no cambiarla' : 'Mínimo 8 caracteres' }}</span>
                <input name="p" type="password" [(ngModel)]="form.password" [required]="!editandoId" minlength="8" autocomplete="new-password" /></label>
              <label>Rol
                <select name="r" [(ngModel)]="form.rol" required>
                  <option value="Administrador">Administrador</option><option value="Encargado">Encargado de sucursal</option><option value="Cajero">Cajero</option>
                </select></label>
              <label>Sucursal @if (form.rol !== 'Administrador') { <span class="hint">Obligatoria</span> }
                <select name="s" [(ngModel)]="form.sucursal_id" [required]="form.rol !== 'Administrador'">
                  <option [ngValue]="null">{{ form.rol === 'Administrador' ? 'Todas (sin asignar)' : 'Seleccione…' }}</option>
                  @for (s of sucursales(); track s.id) { <option [ngValue]="s.id">{{ s.nombre }}{{ s.activa ? '' : ' (inactiva)' }}</option> }
                </select></label>
            </div>
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          </div>
          <footer><button type="button" class="btn" (click)="modal.set(false)">Cancelar</button><button class="btn primary" [disabled]="guardando() || !f.valid">Guardar</button></footer>
        </form>
      </div>
    }`,
})
export class UsuariosPage implements OnInit {
  private api = inject(AdministracionApi);
  private toast = inject(ToastService);

  readonly usuarios = signal<Usuario[]>([]);
  readonly sucursales = signal<Sucursal[]>([]);
  readonly cargando = signal(true);
  readonly modal = signal(false);
  readonly guardando = signal(false);
  readonly error = signal('');
  editandoId = 0;
  form = this.vacio();

  ngOnInit() {
    this.cargar();
    this.api.sucursales().subscribe((r) => this.sucursales.set(r.sucursales));
  }

  cargar() { this.api.usuarios().subscribe({ next: (u) => { this.usuarios.set(u); this.cargando.set(false); }, error: (e) => { this.cargando.set(false); this.toast.error(mensajeError(e)); } }); }

  abrirNuevo() { this.editandoId = 0; this.form = this.vacio(); this.error.set(''); this.modal.set(true); }
  abrirEditar(u: Usuario) {
    this.editandoId = u.id; this.error.set('');
    this.form = { nombre: u.nombre, apellidos: u.apellidos, email: u.email, password: '', rol: u.rol as string, sucursal_id: u.sucursal_id };
    this.modal.set(true);
  }

  guardar() {
    this.guardando.set(true); this.error.set('');
    const f = this.form;
    const op = this.editandoId
      ? this.api.editarUsuario(this.editandoId, { nombre: f.nombre, apellidos: f.apellidos, rol: f.rol, sucursal_id: f.sucursal_id, password: f.password || null })
      : this.api.registrarUsuario({ nombre: f.nombre, apellidos: f.apellidos, email: f.email, password: f.password, rol: f.rol, sucursal_id: f.sucursal_id });
    op.subscribe({
      next: () => { this.guardando.set(false); this.modal.set(false); this.toast.ok('Usuario guardado.'); this.cargar(); },
      error: (e) => { this.guardando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  desactivar(u: Usuario) {
    if (!confirm(`¿Desactivar a ${u.nombre} ${u.apellidos}?`)) return;
    this.api.desactivarUsuario(u.id).subscribe({ next: () => { this.toast.ok('Usuario desactivado.'); this.cargar(); }, error: (e) => this.toast.error(mensajeError(e)) });
  }
  activar(u: Usuario) {
    this.api.editarUsuario(u.id, { activo: true }).subscribe({ next: () => { this.toast.ok('Usuario activado.'); this.cargar(); }, error: (e) => this.toast.error(mensajeError(e)) });
  }

  private vacio() { return { nombre: '', apellidos: '', email: '', password: '', rol: 'Cajero', sucursal_id: null as number | null }; }
}
