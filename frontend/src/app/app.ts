import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ToastComponent } from './core/ui/toast.component';
import { ToastService } from './core/ui/toast.service';

export const MSG_CUOTA = 'No hay espacio para guardar más datos sin conexión. Libere espacio o sincronice las operaciones pendientes.';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, ToastComponent],
  template: `<router-outlet /><app-toasts />`,
})
export class App {
  private toast = inject(ToastService);

  constructor() {
    // §5.2: se pide al navegador que no borre IndexedDB cuando le falte espacio
    void navigator.storage?.persist?.();
    // y si el almacenamiento se llena, se avisa con un mensaje claro en vez de fallar en silencio
    window.addEventListener('unhandledrejection', (e) => { if ((e.reason as { name?: string })?.name === 'QuotaExceededError') this.toast.error(MSG_CUOTA); });
  }
}
