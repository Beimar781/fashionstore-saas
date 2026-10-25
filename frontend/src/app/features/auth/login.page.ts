import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { ConnectivityService } from '../../core/offline/connectivity.service';
import { PasswordFieldComponent } from '../../core/ui/password-field.component';
import { mensajeError } from '../../core/ui/toast.service';
import { AuthLayoutComponent } from './auth-layout.component';

/** CU-02 · Inicio de sesión con código de empresa, correo y contraseña. */
@Component({
  selector: 'app-login',
  imports: [FormsModule, RouterLink, PasswordFieldComponent, AuthLayoutComponent],
  template: `
    <app-auth-layout>
      <h2>Iniciar sesión</h2>
      <p class="muted small">Ingrese el código de su empresa. El SuperAdministrador de la plataforma lo deja vacío.</p>
      <form class="stack" (ngSubmit)="entrar()" #f="ngForm">
        <label>Código de empresa
          <input name="codigo" [(ngModel)]="codigo" autocomplete="organization" placeholder="EMP-A" />
        </label>
        <label>Correo
          <input name="email" type="email" [(ngModel)]="email" required autocomplete="username" />
        </label>
        <label>Contraseña
          <app-password-field [(valor)]="password" />
        </label>
        <a class="olvide" routerLink="/olvide-password">¿Olvidaste tu contraseña?</a>
        @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
        @if (!net.online()) { <div class="alert warn">Sin conexión: solo puede continuar con una sesión previa en este dispositivo.</div> }
        <button class="btn primary" type="submit" [disabled]="cargando() || !f.valid || !password">{{ cargando() ? 'Ingresando…' : 'Ingresar' }}</button>
      </form>
    </app-auth-layout>`,
  styles: `
    .olvide { justify-self: end; font-size: .88rem; margin-top: -.35rem; }`,
})
export class LoginPage {
  private auth = inject(AuthService);
  private router = inject(Router);
  readonly net = inject(ConnectivityService);

  codigo = ''; email = ''; password = '';
  readonly error = signal('');
  readonly cargando = signal(false);

  entrar() {
    this.error.set('');
    const codigo = this.codigo.trim() || null;
    if (!this.net.online()) {
      // CU-02, flujos alternativos sin conexión
      if (this.auth.tieneSesionLocal(this.email, codigo)) { void this.router.navigateByUrl(this.auth.rutaInicial()); return; }
      this.error.set('Se requiere conexión para el primer inicio de sesión.');
      return;
    }
    this.cargando.set(true);
    this.auth.login({ codigo_empresa: codigo, email: this.email.trim(), password: this.password }).subscribe({
      next: () => { this.cargando.set(false); void this.router.navigateByUrl(this.auth.rutaInicial()); },
      error: (e) => { this.cargando.set(false); this.error.set(mensajeError(e)); },
    });
  }
}
