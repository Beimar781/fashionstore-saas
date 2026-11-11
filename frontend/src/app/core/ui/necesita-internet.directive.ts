import { Directive, ElementRef, effect, inject, input } from '@angular/core';
import { ConnectivityService } from '../offline/connectivity.service';
import { ToastService } from './toast.service';

export const MSG_NECESITA_INTERNET = 'Esta función necesita Internet.';

/**
 * Marca un botón que solo funciona con conexión (reportes con IA, exportes, planes). Sin red el botón se ve apagado, explica el motivo al pasar el cursor
 * y, si se toca, avisa «Esta función necesita Internet.» en vez de lanzar la petición y mostrar un error.
 */
@Directive({ selector: '[necesitaInternet]' })
export class NecesitaInternetDirective {
  private el = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;
  private red = inject(ConnectivityService);
  private toast = inject(ToastService);

  /** Motivo que se muestra mientras no hay conexión (por defecto el aviso general). */
  readonly necesitaInternet = input<string>('');

  constructor() {
    effect(() => {
      const sinRed = !this.red.online();
      this.el.classList.toggle('sin-internet', sinRed);
      this.el.setAttribute('aria-disabled', String(sinRed));
      if (sinRed) this.el.title = this.necesitaInternet() || MSG_NECESITA_INTERNET; else this.el.removeAttribute('title');
    });
    // en la fase de captura, antes que el (click) de la propia pantalla
    this.el.addEventListener('click', (e) => {
      if (this.red.online()) return;
      e.stopImmediatePropagation();
      e.preventDefault();
      this.toast.aviso(this.necesitaInternet() || MSG_NECESITA_INTERNET);
    }, true);
  }
}
