import { Component, DestroyRef, inject, input, signal } from '@angular/core';
import { ConnectivityService } from '../offline/connectivity.service';
import { LecturasLocalesService } from '../offline/lecturas-locales.service';
import { MSG_SIN_CONEXION } from './toast.service';

export const MSG_SIN_DATOS_SIN_RED = 'Esta pantalla necesita Internet: todavía no hay datos guardados de ella en este dispositivo. Ábrala una vez con conexión para tenerlos disponibles.';

/** Mensaje de lista vacía que no engaña: sin conexión no se puede saber si «no hay nada» o simplemente no se pudo consultar. */
@Component({
  selector: 'app-vacio',
  template: `@if (red.online() || !(fallo() || lecturas.falloSinCopia())) { <div class="card empty"><ng-content /></div> } @else { <div class="card empty" role="status">${MSG_SIN_DATOS_SIN_RED}</div> }`,
})
export class VacioComponent {
  readonly red = inject(ConnectivityService);
  readonly lecturas = inject(LecturasLocalesService);
  /** La pantalla puede avisar que su consulta falló sin copia guardada (si no, se usa el aviso global de la pantalla actual). */
  readonly fallo = input(false);
}

/** «Cargando…» que siempre termina: sin conexión explica que faltan datos guardados y, si tarda demasiado, avisa en vez de girar para siempre. */
@Component({
  selector: 'app-cargando',
  template: `@if (!red.online()) { <div class="empty" role="status">${MSG_SIN_DATOS_SIN_RED}</div> } @else if (tardando()) { <div class="empty" role="status">Está tardando más de lo normal. Revise su conexión y vuelva a abrir esta pantalla.</div> } @else { <div class="empty">Cargando…</div> }`,
})
export class CargandoComponent {
  readonly red = inject(ConnectivityService);
  readonly tardando = signal(false);
  constructor() { const t = setTimeout(() => this.tardando.set(true), 12_000); inject(DestroyRef).onDestroy(() => clearTimeout(t)); }
}

export const MSG_NECESITA_INTERNET_PANTALLA = 'Esta función necesita Internet.';

/** Alerta de error de una pantalla: la falta de conexión no es un fallo (ámbar y con el motivo); cualquier otro error sigue en rojo. */
@Component({
  selector: 'app-error',
  template: `@if (texto() === sinConexion) { <div class="alert warn" role="status">${MSG_NECESITA_INTERNET_PANTALLA}</div> } @else { <div class="alert danger" role="alert">{{ texto() }}</div> }`,
})
export class ErrorComponent {
  readonly texto = input.required<string>();
  readonly sinConexion = MSG_SIN_CONEXION;
}
