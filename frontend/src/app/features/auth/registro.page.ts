import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { PasswordFieldComponent } from '../../core/ui/password-field.component';
import { mensajeError } from '../../core/ui/toast.service';
import { AuthLayoutComponent } from './auth-layout.component';

/** CU-01 · Registrar cuenta de cliente en la tienda (empresa) que se visita. */
@Component({
  selector: 'app-registro',
  imports: [FormsModule, RouterLink, PasswordFieldComponent, AuthLayoutComponent],
  template: `
    <app-auth-layout>
      <h2>Crear cuenta de cliente</h2>
      <p class="muted small">Pida el código de la tienda en la que desea comprar. Su cuenta solo existirá en esa tienda.</p>
      <form class="stack" (ngSubmit)="registrar()" #f="ngForm">
        <label>Código de la tienda<input name="codigo" [(ngModel)]="codigo" required placeholder="EMP-A" autocomplete="organization" /></label>
        <div class="form-grid" style="grid-template-columns:1fr 1fr">
          <label>Nombre<input name="nombre" [(ngModel)]="nombre" required autocomplete="given-name" /></label>
          <label>Apellidos<input name="apellidos" [(ngModel)]="apellidos" autocomplete="family-name" /></label>
        </div>
        <label>Correo<input name="email" type="email" [(ngModel)]="email" required autocomplete="email" /></label>
        <label>Contraseña <span class="hint">(mínimo 8 caracteres)</span><app-password-field [(valor)]="password" /></label>
        @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
        <button class="btn primary" type="submit" [disabled]="cargando() || !f.valid || password.length < 8">{{ cargando() ? 'Creando…' : 'Crear cuenta' }}</button>
        <p class="small muted">¿Ya tiene cuenta? <a routerLink="/login">Iniciar sesión</a></p>
      </form>
    </app-auth-layout>`,
})
export class RegistroPage {
  private auth = inject(AuthService);
  private router = inject(Router);

  codigo = ''; nombre = ''; apellidos = ''; email = ''; password = '';
  readonly error = signal('');
  readonly cargando = signal(false);

  registrar() {
    this.cargando.set(true); this.error.set('');
    this.auth.registrarCliente({ codigo_empresa: this.codigo.trim(), nombre: this.nombre.trim(), apellidos: this.apellidos.trim(), email: this.email.trim(), password: this.password }).subscribe({
      next: () => { this.cargando.set(false); void this.router.navigateByUrl(this.auth.rutaInicial()); },
      error: (e) => { this.cargando.set(false); this.error.set(mensajeError(e)); },
    });
  }
}
