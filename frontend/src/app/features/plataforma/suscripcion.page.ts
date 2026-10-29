import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { PlataformaApi } from '../../core/api/plataforma.api';
import { Empresa, Plan, SuscripcionDetalle } from '../../core/models';
import { ToastService, mensajeError } from '../../core/ui/toast.service';

/** CU-35 · Gestionar suscripciones de empresas. La ruta entrega el id de la empresa como input. */
@Component({
  selector: 'app-suscripcion',
  imports: [FormsModule, DatePipe, RouterLink],
  template: `
    <div class="page">
      <p class="small"><a routerLink="/plataforma/empresas">← Empresas</a></p>
      <div class="page-head">
        <div><h1>Suscripción de {{ empresa()?.razon_social ?? '…' }}</h1><p>{{ empresa()?.codigo }} · empresa {{ empresa()?.estado }}</p></div>
        <button class="btn primary" (click)="abrir()">Asignar / cambiar / renovar plan</button>
      </div>

      @if (detalle(); as d) {
        <div class="grid cols-2">
          <section class="card pad stack">
            <h2>Estado actual</h2>
            @if (d.vigente; as v) {
              <div class="row"><span class="badge" [class.ok]="v.estado === 'ACTIVA'" [class.danger]="v.estado !== 'ACTIVA'">{{ v.estado }}</span><strong>Plan {{ v.plan.nombre }}</strong></div>
              <div class="muted small">Del {{ v.fecha_inicio | date: 'dd/MM/yyyy' }} al {{ v.fecha_vencimiento | date: 'dd/MM/yyyy' }} · pago {{ v.forma_pago ?? '—' }}</div>
              @if (v.estado !== 'ACTIVA') { <div class="alert warn">La empresa está restringida (RN05) hasta que se renueve o reactive la suscripción.</div> }
              @if (v.estado === 'ACTIVA') {
                <div class="row">
                  <button class="btn sm" (click)="cambiarEstado('SUSPENDIDA')">Suspender</button>
                  <button class="btn sm danger" (click)="cambiarEstado('CANCELADA')">Cancelar</button>
                </div>
              }
            } @else { <div class="alert warn">La empresa no tiene suscripción.</div> }
          </section>
          <section class="card pad stack">
            <h2>Uso del plan</h2>
            <div class="row between"><strong>{{ d.uso.sucursales_activas }} de {{ d.uso.limite ?? '—' }}</strong><span class="muted small">sucursales activas</span></div>
            <div class="meter" [class.full]="d.uso.limite !== null && d.uso.sucursales_activas >= d.uso.limite"><span [style.width.%]="porcentaje(d)"></span></div>
          </section>
        </div>

        <h2 style="margin:1.5rem 0 .75rem">Historial</h2>
        <div class="card table-wrap">
          <table>
            <thead><tr><th>Plan</th><th>Inicio</th><th>Vencimiento</th><th>Estado</th><th>Pago</th><th class="right">Monto (Bs)</th></tr></thead>
            <tbody>
              @for (h of d.historial; track h.id) {
                <tr><td><strong>{{ h.plan.nombre }}</strong></td><td>{{ h.fecha_inicio | date: 'dd/MM/yyyy' }}</td><td>{{ h.fecha_vencimiento | date: 'dd/MM/yyyy' }}</td>
                  <td><span class="badge" [class.ok]="h.estado === 'ACTIVA'">{{ h.estado }}</span></td><td>{{ h.forma_pago ?? '—' }}</td><td class="right">{{ h.monto }}</td></tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>

    @if (modal()) {
      <div class="overlay" (click)="modal.set(false)">
        <form class="modal" (click)="$event.stopPropagation()" (ngSubmit)="guardar()" #f="ngForm" role="dialog" aria-modal="true">
          <header><h2>Asignar plan</h2><button type="button" class="btn sm ghost" (click)="modal.set(false)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <div class="form-grid">
              <label class="full">Plan
                <select name="plan" [(ngModel)]="form.plan_id" required>
                  <option [ngValue]="null" disabled>Seleccione…</option>
                  @for (p of planes(); track p.id) { <option [ngValue]="p.id">{{ p.nombre }} · hasta {{ p.max_sucursales }} sucursales · Bs {{ p.precio }}{{ p.es_prueba ? ' · 1 mes, una sola vez' : '' }}</option> }
                </select></label>
              <label>Inicio<input name="fi" type="date" [(ngModel)]="form.fecha_inicio" required /></label>
              @if (esPrueba()) { <div class="full small muted">La prueba gratuita dura 1 mes y la empresa puede usarla una sola vez.</div> } @else {
              <label>Duración<select name="d" [(ngModel)]="form.duracion_meses"><option [ngValue]="1">1 mes</option><option [ngValue]="3">3 meses</option><option [ngValue]="6">6 meses</option><option [ngValue]="12">12 meses</option></select></label>
              }
              <label class="full">Forma de pago <span class="hint">Registro simulado, sin cobro real</span>
                <select name="fp" [(ngModel)]="form.forma_pago"><option value="EFECTIVO">Efectivo</option><option value="TRANSFERENCIA">Transferencia</option><option value="QR">QR</option></select></label>
            </div>
            @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          </div>
          <footer><button type="button" class="btn" (click)="modal.set(false)">Cancelar</button><button class="btn primary" [disabled]="guardando() || !f.valid">Confirmar</button></footer>
        </form>
      </div>
    }`,
})
export class SuscripcionPage implements OnInit {
  readonly id = input.required<string>(); // /plataforma/empresas/:id/suscripcion (withComponentInputBinding)
  private api = inject(PlataformaApi);
  private toast = inject(ToastService);

  readonly detalle = signal<SuscripcionDetalle | null>(null);
  readonly empresa = signal<Empresa | null>(null);
  readonly planes = signal<Plan[]>([]);
  esPrueba() { return !!this.planes().find((p) => p.id === this.form.plan_id)?.es_prueba; }
  readonly modal = signal(false);
  readonly guardando = signal(false);
  readonly error = signal('');
  form = { plan_id: null as number | null, fecha_inicio: new Date().toISOString().slice(0, 10), duracion_meses: 12, forma_pago: 'QR' };

  ngOnInit() { this.cargar(); }

  cargar() {
    const id = Number(this.id());
    this.api.empresas().subscribe((es) => this.empresa.set(es.find((e) => e.id === id) ?? null));
    this.api.suscripcion(id).subscribe({ next: (d) => this.detalle.set(d), error: (e) => this.toast.error(mensajeError(e)) });
  }

  porcentaje(d: SuscripcionDetalle) { return d.uso.limite ? Math.min(100, (d.uso.sucursales_activas / d.uso.limite) * 100) : 0; }

  abrir() {
    this.error.set('');
    this.api.planes().subscribe((p) => this.planes.set(p.filter((x) => x.activo)));
    this.modal.set(true);
  }

  guardar() {
    this.guardando.set(true); this.error.set('');
    this.api.asignarPlan(Number(this.id()), this.form).subscribe({
      next: () => { this.guardando.set(false); this.modal.set(false); this.toast.ok('Suscripción registrada.'); this.cargar(); },
      error: (e) => { this.guardando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  cambiarEstado(estado: 'SUSPENDIDA' | 'CANCELADA') {
    if (!confirm(`¿${estado === 'SUSPENDIDA' ? 'Suspender' : 'Cancelar'} la suscripción? La empresa quedará restringida.`)) return;
    this.api.suspenderSuscripcion(Number(this.id()), estado).subscribe({ next: () => { this.toast.ok('Estado actualizado.'); this.cargar(); }, error: (e) => this.toast.error(mensajeError(e)) });
  }
}
