import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AdministracionApi } from '../../core/api/administracion.api';
import { AuthService } from '../../core/auth/auth.service';
import { UsoPlan } from '../../core/models';

/** Consulta del plan de la empresa. Es lo único habilitado cuando la suscripción no está vigente (RN05). */
@Component({
  selector: 'app-mi-plan',
  imports: [DatePipe, RouterLink],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Mi plan</h1><p>Plan contratado, vigencia y funcionalidades habilitadas para su empresa.</p></div></div>

      @if (auth.restringido()) {
        <div class="alert danger" role="alert" style="margin-bottom:1rem">
          <strong>La suscripción de su empresa no está vigente.</strong> Solo puede consultar su plan hasta que el administrador de la plataforma la renueve.
        </div>
      }

      @if (sus(); as s) {
        <div class="grid cols-2">
          <section class="card pad stack">
            <div class="row between"><h2>Plan {{ s.plan.nombre }}</h2>
              <span class="badge" [class.ok]="s.estado === 'ACTIVA'" [class.danger]="s.estado !== 'ACTIVA'">{{ s.estado }}</span></div>
            <div class="muted">Vigente del {{ s.fecha_inicio | date: 'dd/MM/yyyy' }} al <strong>{{ s.fecha_vencimiento | date: 'dd/MM/yyyy' }}</strong></div>
            <ul>
              <li><strong>Hasta {{ s.plan.max_sucursales }}</strong> sucursales activas</li>
              <li [class.no]="!s.plan.reportes_convencionales">Reportes convencionales</li>
              <li [class.no]="!s.plan.offline">Operación offline</li>
              <li [class.no]="!s.plan.reportes_ia">Reportes generativos con IA</li>
            </ul>
          </section>
          <section class="card pad stack">
            <h2>Uso del plan</h2>
            @if (uso(); as u) {
              <div class="row between"><strong>{{ u.activas }} de {{ u.limite }}</strong><span class="muted small">sucursales activas</span></div>
              <div class="meter" [class.full]="u.disponibles === 0"><span [style.width.%]="(u.activas / (u.limite || 1)) * 100"></span></div>
              <a class="btn" routerLink="/empresa/sucursales">Administrar sucursales</a>
            } @else if (!auth.restringido()) { <p class="muted">Cargando…</p> }
            @else { <p class="muted small">El detalle de uso no está disponible mientras la suscripción no esté vigente.</p> }
          </section>
        </div>
      } @else { <div class="empty">Cargando…</div> }
    </div>`,
  styles: `
    ul { list-style: none; padding: 0; margin: 0; display: grid; gap: .35rem; }
    li::before { content: '✓'; color: var(--ok); font-weight: 700; margin-right: .5rem; }
    li.no { color: var(--muted); text-decoration: line-through; } li.no::before { content: '✕'; color: var(--danger); }`,
})
export class MiPlanPage implements OnInit {
  readonly auth = inject(AuthService);
  private api = inject(AdministracionApi);
  readonly uso = signal<UsoPlan | null>(null);
  readonly sus = () => this.auth.sesion()?.suscripcion ?? null;

  ngOnInit() {
    // Se refresca el contexto (el plan pudo cambiar) y, si la empresa puede operar, su uso de sucursales.
    this.auth.actualizarSesion().subscribe({
      next: (s) => { if (!s.restringido) this.api.sucursales().subscribe((r) => this.uso.set(r.uso_plan)); },
      error: () => { /* sin conexión: se muestra el contexto guardado */ },
    });
  }
}
