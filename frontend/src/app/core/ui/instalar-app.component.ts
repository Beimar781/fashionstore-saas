import { Component, OnInit, signal } from '@angular/core';

/** §5.2 · Botón «Instalar aplicación» (PWA): usa el aviso del navegador (`beforeinstallprompt`) y se oculta si la app ya está instalada.
 *  En iOS, que no tiene ese aviso, muestra la instrucción de «Compartir → Añadir a pantalla de inicio». */
@Component({
  selector: 'app-instalar-app',
  template: `
    @if (!instalada()) {
      @if (aviso()) { <button type="button" class="btn sm" (click)="instalar()">⬇ Instalar aplicación</button> }
      @else if (esIos) { <button type="button" class="btn sm" (click)="ayuda.set(!ayuda())">Instalar aplicación</button>
        @if (ayuda()) { <span class="small muted" role="status">En Safari: Compartir → Añadir a pantalla de inicio.</span> } }
    }`,
})
export class InstalarAppComponent implements OnInit {
  readonly aviso = signal<any>(null);
  readonly instalada = signal(this.estaInstalada());
  readonly ayuda = signal(false);
  readonly esIos = /iphone|ipad|ipod/i.test(navigator.userAgent);

  ngOnInit() {
    window.addEventListener('beforeinstallprompt', (e) => { e.preventDefault(); this.aviso.set(e); });
    window.addEventListener('appinstalled', () => { this.instalada.set(true); this.aviso.set(null); });
  }

  async instalar() {
    const evento = this.aviso();
    if (!evento) return;
    await evento.prompt();
    this.aviso.set(null);
  }

  private estaInstalada() {
    return window.matchMedia?.('(display-mode: standalone)').matches || (navigator as any).standalone === true;
  }
}
