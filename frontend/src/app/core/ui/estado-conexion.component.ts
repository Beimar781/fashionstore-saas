import { Component, computed, inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../auth/auth.service';
import { ColaOperacionesService } from '../offline/cola-operaciones.service';
import { ConnectivityService } from '../offline/connectivity.service';
import { rutaDeLaCola } from '../offline/rutas-cola';

/** Indicador permanente de la barra superior: en línea, sin conexión o sincronizando, con el número de operaciones pendientes. Al tocarlo abre el detalle de la cola. */
@Component({
  selector: 'app-estado-conexion',
  template: `
    <button type="button" class="estado" [class.linea]="estado() === 'linea'" [class.sin]="estado() === 'sin'" [class.sync]="estado() === 'sync'" (click)="abrir()" [title]="titulo()" aria-label="Estado de la conexión y operaciones pendientes">
      <span class="punto" aria-hidden="true"></span>{{ texto() }}@if (pendientes()) { <span class="cuenta" [attr.aria-label]="pendientes() + ' operaciones pendientes'">{{ pendientes() }}</span> }
    </button>`,
  styles: `
    .estado { display: inline-flex; align-items: center; gap: .4rem; border: 1px solid var(--line); background: var(--surface); border-radius: 999px; padding: .2rem .7rem; font: inherit; font-size: .8rem; cursor: pointer; color: var(--ink); }
    .punto { width: .55rem; height: .55rem; border-radius: 50%; background: #1e7a4f; } .sin .punto { background: #b8741a; } .sync .punto { background: #2563b8; animation: pulso 1s infinite; }
    .cuenta { background: #9a5b00; color: #fff; border-radius: 999px; padding: 0 .45rem; font-weight: 600; }
    @keyframes pulso { 50% { opacity: .35; } }`,
})
export class EstadoConexionComponent {
  private red = inject(ConnectivityService);
  private cola = inject(ColaOperacionesService);
  private auth = inject(AuthService);
  private router = inject(Router);

  readonly pendientes = computed(() => this.cola.pendientes().length);
  readonly estado = computed<'linea' | 'sin' | 'sync'>(() => (this.cola.sincronizando() ? 'sync' : this.red.online() ? 'linea' : 'sin'));
  readonly texto = computed(() => ({ linea: 'En línea', sin: 'Sin conexión', sync: 'Sincronizando…' })[this.estado()]);
  readonly titulo = computed(() => `${this.texto()}${this.pendientes() ? ` · ${this.pendientes()} operación(es) por sincronizar` : ''}. Toque para ver el detalle.`);

  abrir() { const ruta = rutaDeLaCola(this.auth.rol()); if (ruta) void this.router.navigateByUrl(ruta); }
}
