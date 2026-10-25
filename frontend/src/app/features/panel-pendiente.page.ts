import { Component, inject, signal } from '@angular/core';
import { AuthService } from '../core/auth/auth.service';
import { ConfirmarSalidaComponent } from '../core/ui/confirmar-salida.component';

/** Paneles de Encargado, Cajero y Cliente: sus casos de uso (reservas, punto de venta, catálogo) llegan en el Lote 2. */
@Component({
  selector: 'app-panel-pendiente',
  imports: [ConfirmarSalidaComponent],
  template: `
    <div class="centro">
      <div class="card pad">
        <h2>Panel de {{ auth.rol() }}</h2>
        <p class="muted">Sesión iniciada en <strong>{{ auth.sesion()?.empresa?.razon_social }}</strong>
          @if (auth.sesion()?.usuario?.sucursal_nombre) { · sucursal {{ auth.sesion()?.usuario?.sucursal_nombre }} }.
          Este panel se habilita con los casos de uso de operación comercial.</p>
        <button class="btn" (click)="confirmar.set(true)">Cerrar sesión</button>
      </div>
    </div>
    @if (confirmar()) { <app-confirmar-salida (cancelar)="confirmar.set(false)" (confirmar)="auth.cerrarSesion()" /> }`,
  styles: `.centro { min-height: 100vh; display: grid; place-items: center; padding: 1rem; } .card { max-width: 480px; display: grid; gap: .8rem; }`,
})
export class PanelPendientePage {
  readonly auth = inject(AuthService);
  readonly confirmar = signal(false);
}
