import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { mensajeError } from '../../core/ui/toast.service';
import { AuthLayoutComponent } from './auth-layout.component';

/** CU-02 (extensión) · Solicitud de enlace para restablecer la contraseña. */
@Component({
  selector: 'app-olvide-password',
  imports: [FormsModule, RouterLink, AuthLayoutComponent],
  template: `
    <app-auth-layout>
      <h2>Recuperar contraseña</h2>
      @if (enviado()) {
        <div class="alert ok" role="status">{{ enviado() }}</div>
        <p class="muted small">El enlace vence en 60 minutos y solo se puede usar una vez. Revise también la carpeta de spam.</p>
        <a class="btn" routerLink="/login">Volver a iniciar sesión</a>
      } @else {
        <p class="muted small">Ingrese el código de su empresa y su correo. Le enviaremos un enlace para crear una contraseña nueva. El SuperAdministrador deja el código vacío.</p>
        <form class="stack" (ngSubmit)="enviar()" #f="ngForm">
          <label>Código de empresa
            <input name="codigo" [(ngModel)]="codigo" autocomplete="organization" placeholder="EMP-A" />
          </label>
          <label>Correo
            <input name="email" type="email" [(ngModel)]="email" required autocomplete="username" />
          </label>
          @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          <button class="btn primary" type="submit" [disabled]="cargando() || !f.valid">{{ cargando() ? 'Enviando…' : 'Enviar enlace' }}</button>
          <a class="volver" routerLink="/login">Volver a iniciar sesión</a>
        </form>
      }
    </app-auth-layout>`,
  styles: `.volver { justify-self: center; font-size: .9rem; }`,
})
export class OlvidePasswordPage {
  private auth = inject(AuthService);
  codigo = ''; email = '';
  readonly error = signal('');
  readonly enviado = signal('');
  readonly cargando = signal(false);

  enviar() {
    this.error.set(''); this.cargando.set(true);
    this.auth.olvidePassword({ codigo_empresa: this.codigo.trim() || null, email: this.email.trim() }).subscribe({
      next: (r) => { this.cargando.set(false); this.enviado.set(r.detail); },
      error: (e) => { this.cargando.set(false); this.error.set(mensajeError(e)); },
    });
  }
}
