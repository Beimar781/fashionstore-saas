import { Component, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { PasswordFieldComponent } from '../../core/ui/password-field.component';
import { mensajeError } from '../../core/ui/toast.service';
import { AuthLayoutComponent } from './auth-layout.component';

/** CU-02 (extensión) · Nueva contraseña a partir del enlace enviado por correo (/restablecer-password?token=...). */
@Component({
  selector: 'app-restablecer-password',
  imports: [FormsModule, RouterLink, PasswordFieldComponent, AuthLayoutComponent],
  template: `
    <app-auth-layout>
      <h2>Nueva contraseña</h2>
      @if (listo()) {
        <div class="alert ok" role="status">{{ listo() }}</div>
        <a class="btn primary" routerLink="/login">Iniciar sesión</a>
      } @else if (!token()) {
        <div class="alert danger" role="alert">El enlace no es válido. Solicite uno nuevo.</div>
        <a class="btn" routerLink="/olvide-password">Solicitar nuevo enlace</a>
      } @else {
        <p class="muted small">Elija una contraseña de al menos 8 caracteres.</p>
        <form class="stack" (ngSubmit)="guardar()">
          <label>Nueva contraseña
            <app-password-field nombre="nueva" autocomplete="new-password" [minlength]="8" [(valor)]="password" />
          </label>
          <label>Repetir contraseña
            <app-password-field nombre="repetir" autocomplete="new-password" [minlength]="8" [(valor)]="repetir" />
          </label>
          @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          <button class="btn primary" type="submit" [disabled]="cargando() || password.length < 8 || !repetir">{{ cargando() ? 'Guardando…' : 'Guardar contraseña' }}</button>
        </form>
      }
    </app-auth-layout>`,
})
export class RestablecerPasswordPage {
  private auth = inject(AuthService);
  readonly token = input<string>();  // query param ?token= (withComponentInputBinding)
  password = ''; repetir = '';
  readonly error = signal('');
  readonly listo = signal('');
  readonly cargando = signal(false);

  guardar() {
    this.error.set('');
    if (this.password !== this.repetir) { this.error.set('Las contraseñas no coinciden.'); return; }
    this.cargando.set(true);
    this.auth.restablecerPassword({ token: this.token()!, password: this.password }).subscribe({
      next: (r) => { this.cargando.set(false); this.listo.set(r.detail); },
      error: (e) => { this.cargando.set(false); this.error.set(mensajeError(e)); },
    });
  }
}
