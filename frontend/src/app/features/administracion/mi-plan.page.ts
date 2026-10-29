import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ReportesApi } from '../../core/api/reportes.api';
import { AuthService } from '../../core/auth/auth.service';
import { MiPlan } from '../../core/reportes.models';
import { mensajeError } from '../../core/ui/toast.service';

/** CU-36 · Plan, límites y uso de la empresa. Es lo único habilitado cuando la suscripción no está vigente (RN05); entonces solo se muestra el plan y la vigencia. */
@Component({
  selector: 'app-mi-plan',
  imports: [DatePipe, RouterLink],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Mi plan</h1><p>Plan contratado, vigencia, límites con su uso y funcionalidades habilitadas para su empresa.</p></div></div>

      @if (auth.restringido()) {
        <div class="alert danger" role="alert" style="margin-bottom:1rem">
          <strong>La suscripción de su empresa no está vigente.</strong> Solo puede consultar su plan hasta que el administrador de la plataforma la renueve.
        </div>
      }
      @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
      @if (p(); as m) {
        @for (a of m.alertas; track a) { @if (!auth.restringido()) { <div class="alert warn" role="status" style="margin-bottom:.6rem">{{ a }}</div> } }
        @if (m.plan && m.vigencia) {
          <div class="grid cols-2">
            <section class="card pad stack">
              <div class="row between"><h2>Plan {{ m.plan.nombre }}</h2>
                <span class="badge" [class.ok]="m.vigencia.vigente" [class.danger]="!m.vigencia.vigente">{{ m.vigencia.estado }}</span></div>
              @if (m.plan.descripcion) { <p class="muted small">{{ m.plan.descripcion }}</p> }
              <div class="muted">Vigente del {{ m.vigencia.fecha_inicio | date: 'dd/MM/yyyy' }} al <strong>{{ m.vigencia.fecha_vencimiento | date: 'dd/MM/yyyy' }}</strong>@if (m.vigencia.dias_restantes !== null) { · quedan {{ m.vigencia.dias_restantes }} día(s) }</div>
              <div class="small muted">Precio Bs {{ m.plan.precio }} ({{ m.plan.periodicidad }})</div>
              <h3>Funcionalidades</h3>
              <ul>@for (f of m.funcionalidades; track f.clave) { <li [class.no]="!f.incluida">{{ f.etiqueta }}</li> }</ul>
            </section>
            <section class="card pad stack">
              <h2>Uso del plan</h2>
              @for (l of m.limites; track l.clave) {
                <div class="row between"><strong>{{ l.usado }} de {{ l.limite }}</strong><span class="muted small">{{ l.etiqueta.toLowerCase() }}</span></div>
                <div class="meter" [class.full]="l.alcanzado"><span [style.width.%]="l.porcentaje ?? 0"></span></div>
                @if (l.clave === 'sucursales') { <a class="btn" routerLink="/empresa/sucursales">Administrar sucursales</a> }
              }
              @if (m.consumo.length) {
                <h3>Consumo de la empresa</h3>
                @for (c of m.consumo; track c.clave) { <div class="row between small"><span>{{ c.etiqueta }}</span><strong>{{ c.valor }}</strong></div> }
              } @else if (auth.restringido()) { <p class="muted small">El detalle de uso no está disponible mientras la suscripción no esté vigente.</p> }
            </section>
          </div>
        } @else { <div class="card empty">{{ m.alertas[0] }}</div> }
      } @else if (!error()) { <div class="empty">Cargando…</div> }
    </div>`,
  styles: `
    ul { list-style: none; padding: 0; margin: 0; display: grid; gap: .35rem; }
    li::before { content: '✓'; color: var(--ok); font-weight: 700; margin-right: .5rem; }
    li.no { color: var(--muted); text-decoration: line-through; } li.no::before { content: '✕'; color: var(--danger); }`,
})
export class MiPlanPage implements OnInit {
  readonly auth = inject(AuthService);
  private api = inject(ReportesApi);
  readonly p = signal<MiPlan | null>(null);
  readonly error = signal('');

  ngOnInit() {
    // Se refresca el contexto (el plan pudo cambiar) y se pide el detalle del plan y su uso.
    this.auth.actualizarSesion().subscribe({ next: () => this.cargar(), error: () => this.cargar() });
  }

  private cargar() { this.api.miPlan().subscribe({ next: (m) => this.p.set(m), error: (e) => this.error.set(mensajeError(e)) }); }
}
