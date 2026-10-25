import { Component, output } from '@angular/core';

/** Ventana emergente de confirmación al cerrar sesión. */
@Component({
  selector: 'app-confirmar-salida',
  template: `
    <div class="overlay" (click)="cancelar.emit()" (keydown.escape)="cancelar.emit()">
      <div class="modal confirmar" (click)="$event.stopPropagation()" role="alertdialog" aria-modal="true" aria-labelledby="t-salir">
        <div class="body">
          <h2 id="t-salir">¿Cerrar sesión?</h2>
          <p class="muted">Saldrá de su cuenta en este dispositivo. Para volver a ingresar necesitará su correo y contraseña.</p>
        </div>
        <footer>
          <button class="btn" type="button" (click)="cancelar.emit()">Cancelar</button>
          <button class="btn primary" type="button" (click)="confirmar.emit()">Sí, cerrar sesión</button>
        </footer>
      </div>
    </div>`,
  styles: `.confirmar { width: min(420px, 100%); } .confirmar h2 { font-size: 1.25rem; }`,
})
export class ConfirmarSalidaComponent {
  readonly cancelar = output<void>();
  readonly confirmar = output<void>();
}
