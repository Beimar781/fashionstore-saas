import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CatalogoAdminApi } from '../../../core/api/catalogo-admin.api';
import { ProveedoresApi } from '../../../core/api/proveedores.api';
import { Coleccion } from '../../../core/catalogo.models';
import { Proveedor } from '../../../core/inventario.models';
import { PasswordFieldComponent } from '../../../core/ui/password-field.component';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';

type Pestana = 'proveedores' | 'colecciones';

/** CU-15 · Gestionar proveedores, su acceso al portal y las colecciones que proveen. */
@Component({
  selector: 'app-proveedores',
  imports: [FormsModule, PasswordFieldComponent],
  template: `
    <div class="page">
      <div class="page-head">
        <div><h1>Proveedores</h1><p>Quienes suministran las prendas. Con una cuenta de acceso pueden avisar remisiones y proponer productos.</p></div>
        <button class="btn primary" (click)="abrirNuevo()">+ Nuevo proveedor</button>
      </div>
      <div class="tabs" role="tablist">
        <button role="tab" [class.activa]="pestana() === 'proveedores'" (click)="pestana.set('proveedores')">Proveedores</button>
        <button role="tab" [class.activa]="pestana() === 'colecciones'" (click)="pestana.set('colecciones')">Colecciones por proveedor</button>
      </div>

      @if (pestana() === 'proveedores') {
        <form class="row" style="margin-bottom:.8rem" (ngSubmit)="cargar()">
          <input name="q" [(ngModel)]="q" placeholder="Buscar por nombre o NIT…" style="max-width:320px" /><button class="btn">Buscar</button>
        </form>
        <div class="card table-wrap">
          @if (cargando()) { <div class="empty">Cargando…</div> }
          @else if (!proveedores().length) { <div class="empty">Aún no hay proveedores.</div> }
          @else {
            <table>
              <thead><tr><th>Proveedor</th><th>NIT</th><th>Contacto</th><th>Portal</th><th>Estado</th><th></th></tr></thead>
              <tbody>
                @for (p of proveedores(); track p.id) {
                  <tr>
                    <td><strong>{{ p.nombre_comercial || p.razon_social }}</strong>@if (p.nombre_comercial) { <div class="muted small">{{ p.razon_social }}</div> }</td>
                    <td>{{ p.nit ?? '—' }}</td>
                    <td class="small">{{ p.email ?? '' }}<br />{{ p.telefono ?? '' }}</td>
                    <td>@if (p.tiene_acceso) { <span class="badge ok">Con acceso</span> } @else { <button class="btn sm" (click)="abrirAcceso(p)">Crear acceso</button> }</td>
                    <td><span class="badge" [class.ok]="p.activo" [class.warn]="!p.activo">{{ p.activo ? 'Activo' : 'Inactivo' }}</span></td>
                    <td class="actions"><button class="btn sm" (click)="abrirEditar(p)">Editar</button>
                      @if (p.activo) { <button class="btn sm danger" (click)="cambiarEstado(p, false)">Desactivar</button> } @else { <button class="btn sm" (click)="cambiarEstado(p, true)">Activar</button> }</td>
                  </tr>
                }
              </tbody>
            </table>
          }
        </div>
      } @else {
        <div class="card table-wrap">
          @if (!colecciones().length) { <div class="empty">Aún no hay colecciones.</div> } @else {
            <table>
              <thead><tr><th>Colección</th><th>Temporada</th><th>Proveedor</th></tr></thead>
              <tbody>
                @for (c of colecciones(); track c.id) {
                  <tr><td><strong>{{ c.nombre }}</strong></td><td>{{ c.temporada }}</td>
                    <td><select [ngModel]="c.proveedor_id" (ngModelChange)="vincular(c, $event)" [name]="'col' + c.id" style="max-width:280px">
                      <option [ngValue]="null">Sin proveedor</option>@for (p of activos(); track p.id) { <option [ngValue]="p.id">{{ p.nombre_comercial || p.razon_social }}</option> }</select></td></tr>
                }
              </tbody>
            </table>
          }
        </div>
      }
    </div>

    @if (modal() === 'datos') {
      <div class="overlay" (click)="modal.set(null)">
        <form class="modal" (click)="$event.stopPropagation()" (ngSubmit)="guardar()" #f="ngForm" role="dialog" aria-modal="true">
          <header><h2>{{ editandoId ? 'Editar proveedor' : 'Nuevo proveedor' }}</h2><button type="button" class="btn sm ghost" (click)="modal.set(null)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <div class="form-grid">
              <label class="full">Razón social<input name="r" [(ngModel)]="form.razon_social" /></label>
              <label>Nombre comercial<input name="n" [(ngModel)]="form.nombre_comercial" /></label>
              <label>NIT<input name="nit" [(ngModel)]="form.nit" /></label>
              <label>Correo<input name="e" type="email" [(ngModel)]="form.email" /></label>
              <label>Teléfono<input name="t" [(ngModel)]="form.telefono" /></label>
              <label class="full">Dirección<input name="d" [(ngModel)]="form.direccion" /></label>
            </div>
            <p class="muted small">Obligatorios: razón social y al menos un dato de contacto (correo o teléfono).</p>
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          </div>
          <footer><button type="button" class="btn" (click)="modal.set(null)">Cancelar</button><button class="btn primary" [disabled]="guardando()">Guardar</button></footer>
        </form>
      </div>
    }
    @if (modal() === 'acceso') {
      <div class="overlay" (click)="modal.set(null)">
        <form class="modal" (click)="$event.stopPropagation()" (ngSubmit)="guardarAcceso()" #g="ngForm" role="dialog" aria-modal="true">
          <header><h2>Acceso al portal de proveedores</h2><button type="button" class="btn sm ghost" (click)="modal.set(null)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <p class="muted small">Cuenta para {{ seleccionado?.nombre_comercial || seleccionado?.razon_social }}. Inicia sesión con el código de su empresa.</p>
            <label>Correo<input name="ae" type="email" [(ngModel)]="acceso.email" required /></label>
            <label>Contraseña inicial <span class="hint">(mínimo 8 caracteres)</span><app-password-field [(valor)]="acceso.password" /></label>
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          </div>
          <footer><button type="button" class="btn" (click)="modal.set(null)">Cancelar</button><button class="btn primary" [disabled]="guardando() || !g.valid || acceso.password.length < 8">Crear acceso</button></footer>
        </form>
      </div>
    }`,
})
export class ProveedoresPage implements OnInit {
  private api = inject(ProveedoresApi);
  private catalogo = inject(CatalogoAdminApi);
  private toast = inject(ToastService);

  readonly pestana = signal<Pestana>('proveedores');
  readonly proveedores = signal<Proveedor[]>([]);
  readonly colecciones = signal<Coleccion[]>([]);
  readonly cargando = signal(true);
  readonly modal = signal<'datos' | 'acceso' | null>(null);
  readonly guardando = signal(false);
  readonly error = signal('');
  q = '';
  editandoId = 0;
  seleccionado: Proveedor | null = null;
  form: any = this.vacio();
  acceso = { email: '', password: '' };

  ngOnInit() { this.cargar(); }

  activos() { return this.proveedores().filter((p) => p.activo); }

  cargar() {
    this.api.proveedores({ q: this.q.trim() }).subscribe({
      next: (r) => { this.proveedores.set(r); this.cargando.set(false); },
      error: (e) => { this.cargando.set(false); this.toast.error(mensajeError(e)); },
    });
    this.catalogo.colecciones().subscribe((r) => this.colecciones.set(r));
  }

  abrirNuevo() { this.editandoId = 0; this.form = this.vacio(); this.error.set(''); this.modal.set('datos'); }
  abrirEditar(p: Proveedor) {
    this.editandoId = p.id; this.error.set('');
    this.form = { razon_social: p.razon_social, nombre_comercial: p.nombre_comercial, nit: p.nit ?? '', email: p.email ?? '', telefono: p.telefono ?? '', direccion: p.direccion };
    this.modal.set('datos');
  }
  abrirAcceso(p: Proveedor) { this.seleccionado = p; this.acceso = { email: p.email ?? '', password: '' }; this.error.set(''); this.modal.set('acceso'); }

  guardar() {
    this.guardando.set(true); this.error.set('');
    const cuerpo = { ...this.form };
    (this.editandoId ? this.api.editarProveedor(this.editandoId, cuerpo) : this.api.crearProveedor(cuerpo)).subscribe({
      next: () => { this.guardando.set(false); this.modal.set(null); this.toast.ok('Proveedor guardado.'); this.cargar(); },
      error: (e) => { this.guardando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  guardarAcceso() {
    this.guardando.set(true); this.error.set('');
    this.api.crearAcceso(this.seleccionado!.id, this.acceso).subscribe({
      next: () => { this.guardando.set(false); this.modal.set(null); this.toast.ok('Acceso creado.'); this.cargar(); },
      error: (e) => { this.guardando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  cambiarEstado(p: Proveedor, activar: boolean) {
    if (!activar && !confirm(`¿Desactivar a ${p.nombre_comercial || p.razon_social}?`)) return;
    (activar ? this.api.activarProveedor(p.id) : this.api.desactivarProveedor(p.id)).subscribe({
      next: () => { this.toast.ok(activar ? 'Proveedor activado.' : 'Proveedor desactivado.'); this.cargar(); },
      error: (e) => this.toast.error(mensajeError(e)),
    });
  }

  vincular(c: Coleccion, proveedorId: number | null) {
    this.api.vincularColeccion(c.id, proveedorId).subscribe({
      next: () => { this.toast.ok('Colección actualizada.'); this.cargar(); },
      error: (e) => { this.toast.error(mensajeError(e)); this.cargar(); },
    });
  }

  private vacio() { return { razon_social: '', nombre_comercial: '', nit: '', email: '', telefono: '', direccion: '' }; }
}
