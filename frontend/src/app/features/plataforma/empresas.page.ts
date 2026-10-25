import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { PlataformaApi } from '../../core/api/plataforma.api';
import { Empresa, Plan } from '../../core/models';
import { ToastService, mensajeError } from '../../core/ui/toast.service';

const hoy = () => new Date().toISOString().slice(0, 10);

/** CU-33 · Gestionar empresas (tenants). */
@Component({
  selector: 'app-empresas',
  styles: `.acc { display: flex; gap: .35rem; flex-wrap: wrap; justify-content: flex-end; max-width: 250px; margin-left: auto; }`,
  imports: [FormsModule, RouterLink, DatePipe],
  template: `
    <div class="page">
      <div class="page-head">
        <div><h1>Empresas contratantes</h1><p>Cada empresa tiene su entorno aislado, su administrador y su suscripción.</p></div>
        <button class="btn primary" (click)="abrirNueva()">+ Registrar empresa</button>
      </div>

      <div class="card table-wrap">
        @if (cargando()) { <div class="empty">Cargando…</div> }
        @else if (!empresas().length) { <div class="empty">Aún no hay empresas registradas.</div> }
        @else {
          <table>
            <thead><tr><th>Código</th><th>Razón social</th><th>NIT</th><th>Plan</th><th>Vence</th><th>Estado</th><th></th></tr></thead>
            <tbody>
              @for (e of empresas(); track e.id) {
                <tr>
                  <td><strong>{{ e.codigo }}</strong></td>
                  <td>{{ e.razon_social }}<div class="muted small">{{ e.email_contacto }}</div></td>
                  <td>{{ e.nit }}</td>
                  <td>{{ e.plan ?? '—' }}</td>
                  <td class="nowrap">{{ e.fecha_vencimiento ? (e.fecha_vencimiento | date: 'dd/MM/yyyy') : '—' }}</td>
                  <td>
                    <span class="badge" [class.ok]="e.estado === 'ACTIVA'" [class.warn]="e.estado === 'SUSPENDIDA'" [class.danger]="e.estado === 'CANCELADA'">Empresa {{ e.estado.toLowerCase() }}</span>
                    <div style="margin-top:.25rem"><span class="badge" [class.ok]="e.suscripcion_estado === 'ACTIVA'" [class.danger]="e.suscripcion_estado && e.suscripcion_estado !== 'ACTIVA'">Suscripción {{ (e.suscripcion_estado ?? 'ninguna').toLowerCase() }}</span></div>
                  </td>
                  <td class="actions"><div class="acc">
                    <a class="btn sm" [routerLink]="['/plataforma/empresas', e.id, 'suscripcion']">Suscripción</a>
                    <button class="btn sm" (click)="abrirEditar(e)">Editar</button>
                    @if (e.estado === 'ACTIVA') { <button class="btn sm danger" (click)="suspender(e)">Suspender</button> }
                    @else if (e.estado === 'SUSPENDIDA') { <button class="btn sm" (click)="reactivar(e)">Reactivar</button> }
                  </div></td>
                </tr>
              }
            </tbody>
          </table>
        }
      </div>
    </div>

    @if (modal()) {
      <div class="overlay" (click)="modal.set(null)">
        <form class="modal" (click)="$event.stopPropagation()" (ngSubmit)="guardar()" #f="ngForm" role="dialog" aria-modal="true">
          <header><h2>{{ modal() === 'nueva' ? 'Registrar empresa' : 'Editar empresa' }}</h2><button type="button" class="btn sm ghost" (click)="modal.set(null)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <fieldset>
              <legend>Datos de la empresa</legend>
              <div class="form-grid">
                <label>Código de empresa <span class="hint">Se usa para iniciar sesión</span>
                  <input name="codigo" [(ngModel)]="form.codigo" required [disabled]="modal() === 'editar'" placeholder="EMP-C" /></label>
                <label>NIT<input name="nit" [(ngModel)]="form.nit" required minlength="3" /></label>
                <label class="full">Razón social<input name="rs" [(ngModel)]="form.razon_social" required /></label>
                <label>Correo de contacto<input name="ec" type="email" [(ngModel)]="form.email_contacto" /></label>
                <label>Teléfono<input name="tel" [(ngModel)]="form.telefono" /></label>
              </div>
            </fieldset>
            @if (modal() === 'nueva') {
              <fieldset>
                <legend>Administrador de la empresa</legend>
                <div class="form-grid">
                  <label>Nombre<input name="an" [(ngModel)]="form.admin_nombre" required /></label>
                  <label>Apellidos<input name="aa" [(ngModel)]="form.admin_apellidos" /></label>
                  <label>Correo<input name="ae" type="email" [(ngModel)]="form.admin_email" required /></label>
                  <label>Contraseña temporal <span class="hint">Mínimo 8 caracteres</span><input name="ap" type="password" [(ngModel)]="form.admin_password" required minlength="8" /></label>
                </div>
              </fieldset>
              <fieldset>
                <legend>Suscripción inicial</legend>
                <div class="form-grid">
                  <label>Plan
                    <select name="plan" [(ngModel)]="form.plan_id" required>
                      <option [ngValue]="null" disabled>Seleccione…</option>
                      @for (p of planes(); track p.id) { <option [ngValue]="p.id">{{ p.nombre }} · hasta {{ p.max_sucursales }} sucursales</option> }
                    </select></label>
                  <label>Inicio<input name="fi" type="date" [(ngModel)]="form.fecha_inicio" required /></label>
                  <label>Duración
                    <select name="dur" [(ngModel)]="form.duracion_meses">
                      <option [ngValue]="1">1 mes</option><option [ngValue]="3">3 meses</option><option [ngValue]="6">6 meses</option><option [ngValue]="12">12 meses</option>
                    </select></label>
                  <label>Forma de pago <span class="hint">Registro simulado</span>
                    <select name="fp" [(ngModel)]="form.forma_pago"><option value="EFECTIVO">Efectivo</option><option value="TRANSFERENCIA">Transferencia</option><option value="QR">QR</option></select></label>
                </div>
              </fieldset>
            }
            @if (errorModal()) { <div class="alert danger" role="alert">{{ errorModal() }}</div> }
          </div>
          <footer><button type="button" class="btn" (click)="modal.set(null)">Cancelar</button><button class="btn primary" [disabled]="guardando() || !f.valid">{{ guardando() ? 'Guardando…' : 'Guardar' }}</button></footer>
        </form>
      </div>
    }

    @if (registrada(); as r) {
      <div class="overlay" (click)="registrada.set(null)">
        <div class="modal" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
          <header><h2>Empresa registrada</h2></header>
          <div class="body">
            <div class="alert ok">La empresa quedó creada con su administrador y su suscripción inicial.</div>
            <div class="card pad stack">
              <div><span class="muted small">Código de empresa</span><div><strong>{{ r.codigo }}</strong></div></div>
              <div><span class="muted small">Correo del administrador</span><div><strong>{{ r.administrador_email }}</strong></div></div>
              <div><span class="muted small">Plan</span><div><strong>{{ r.plan }}</strong> · vence {{ r.fecha_vencimiento | date: 'dd/MM/yyyy' }}</div></div>
            </div>
          </div>
          <footer><button class="btn primary" (click)="registrada.set(null)">Entendido</button></footer>
        </div>
      </div>
    }`,
})
export class EmpresasPage implements OnInit {
  private api = inject(PlataformaApi);
  private toast = inject(ToastService);

  readonly empresas = signal<Empresa[]>([]);
  readonly planes = signal<Plan[]>([]);
  readonly cargando = signal(true);
  readonly modal = signal<'nueva' | 'editar' | null>(null);
  readonly guardando = signal(false);
  readonly errorModal = signal('');
  readonly registrada = signal<Empresa | null>(null);
  private editandoId = 0;

  form = this.formVacio();

  ngOnInit() { this.cargar(); }

  cargar() {
    this.api.empresas().subscribe({
      next: (e) => { this.empresas.set(e); this.cargando.set(false); },
      error: (e) => { this.cargando.set(false); this.toast.error(mensajeError(e)); },
    });
  }

  abrirNueva() {
    this.form = this.formVacio();
    this.errorModal.set('');
    this.api.planes().subscribe((p) => { this.planes.set(p.filter((x) => x.activo)); });
    this.modal.set('nueva');
  }

  abrirEditar(e: Empresa) {
    this.editandoId = e.id;
    this.form = { ...this.formVacio(), codigo: e.codigo, nit: e.nit, razon_social: e.razon_social, email_contacto: e.email_contacto ?? '', telefono: e.telefono ?? '' };
    this.errorModal.set('');
    this.modal.set('editar');
  }

  guardar() {
    const f = this.form;
    this.guardando.set(true); this.errorModal.set('');
    if (this.modal() === 'nueva') {
      this.api.registrarEmpresa({
        codigo: f.codigo.trim(), razon_social: f.razon_social, nit: f.nit, email_contacto: f.email_contacto || null, telefono: f.telefono || null,
        administrador: { nombre: f.admin_nombre, apellidos: f.admin_apellidos, email: f.admin_email, password: f.admin_password },
        suscripcion: { plan_id: f.plan_id, fecha_inicio: f.fecha_inicio, duracion_meses: f.duracion_meses, forma_pago: f.forma_pago },
      }).subscribe({
        next: (r) => { this.guardando.set(false); this.modal.set(null); this.registrada.set(r); this.cargar(); },
        error: (e) => { this.guardando.set(false); this.errorModal.set(mensajeError(e)); },
      });
    } else {
      this.api.editarEmpresa(this.editandoId, { razon_social: f.razon_social, nit: f.nit, email_contacto: f.email_contacto || null, telefono: f.telefono || null }).subscribe({
        next: () => { this.guardando.set(false); this.modal.set(null); this.toast.ok('Empresa actualizada.'); this.cargar(); },
        error: (e) => { this.guardando.set(false); this.errorModal.set(mensajeError(e)); },
      });
    }
  }

  suspender(e: Empresa) {
    if (!confirm(`¿Suspender a ${e.razon_social}? Sus usuarios no podrán iniciar sesión; los datos se conservan.`)) return;
    this.api.suspenderEmpresa(e.id).subscribe({ next: () => { this.toast.ok('Empresa suspendida.'); this.cargar(); }, error: (x) => this.toast.error(mensajeError(x)) });
  }

  reactivar(e: Empresa) {
    this.api.reactivarEmpresa(e.id).subscribe({ next: () => { this.toast.ok('Empresa reactivada.'); this.cargar(); }, error: (x) => this.toast.error(mensajeError(x)) });
  }

  private formVacio() {
    return {
      codigo: '', nit: '', razon_social: '', email_contacto: '', telefono: '',
      admin_nombre: '', admin_apellidos: '', admin_email: '', admin_password: '',
      plan_id: null as number | null, fecha_inicio: hoy(), duracion_meses: 12, forma_pago: 'QR',
    };
  }
}
