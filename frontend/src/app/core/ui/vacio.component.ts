import { Component, DestroyRef, inject, signal } from '@angular/core';
import { ConnectivityService } from '../offline/connectivity.service';

export const MSG_SIN_DATOS_SIN_RED = 'Sin conexión: todavía no hay datos guardados de esta pantalla en este dispositivo. Ábrala una vez con Internet para tenerlos disponibles.';

/** Mensaje de lista vacía que no engaña: sin conexión no se puede saber si «no hay nada» o simplemente no se pudo consultar. */
@Component({
  selector: 'app-vacio',
  template: `@if (red.online()) { <div class="card empty"><ng-content /></div> } @else { <div class="card empty" role="status">${MSG_SIN_DATOS_SIN_RED}</div> }`,
})
export class VacioComponent {
  readonly red = inject(ConnectivityService);
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
