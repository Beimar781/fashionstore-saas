import { Component, input, model, signal } from '@angular/core';

/** Campo de contraseña con botón para mostrar/ocultar (ojito). Uso: <app-password-field [(valor)]="password" />. */
@Component({
  selector: 'app-password-field',
  template: `
    <div class="pw">
      <input [name]="nombre()" [type]="ver() ? 'text' : 'password'" [value]="valor()" (input)="valor.set($any($event.target).value)"
        [attr.autocomplete]="autocomplete()" [attr.placeholder]="placeholder() || null" [attr.minlength]="minlength() || null" required />
      <button type="button" class="ojo" (click)="ver.set(!ver())" [attr.aria-label]="ver() ? 'Ocultar contraseña' : 'Mostrar contraseña'" [attr.aria-pressed]="ver()">
        @if (ver()) {
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M3 3l18 18"/><path d="M10.6 6.1A9.8 9.8 0 0 1 12 6c5 0 8.5 4 9.5 6a14 14 0 0 1-2.9 3.8M6.5 7.5C4.4 9 2.9 11 2.5 12c1 2 4.500 6 9.5 6 1.300 0 2.500-.3 3.600-.7"/><path d="M9.9 9.9a3 3 0 0 0 4.200 4.200"/>
          </svg>
        } @else {
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M2.500 12C3.500 10 7 6 12 6s8.500 4 9.500 6c-1 2-4.500 6-9.500 6S3.500 14 2.500 12z"/><circle cx="12" cy="12" r="3"/>
          </svg>
        }
      </button>
    </div>`,
  styles: `
    .pw { position: relative; }
    .pw input { padding-right: 2.8rem; }
    .ojo { position: absolute; top: 50%; right: .35rem; transform: translateY(-50%); border: 0; background: transparent; color: var(--muted);
      width: 2.2rem; height: 2.2rem; display: grid; place-items: center; border-radius: 8px; cursor: pointer; }
    .ojo:hover { color: var(--ink); background: rgba(29,26,34,.06); }
    .ojo:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }`,
})
export class PasswordFieldComponent {
  readonly valor = model('');
  readonly nombre = input('password');
  readonly autocomplete = input('current-password');
  readonly placeholder = input('');
  readonly minlength = input(0);
  readonly ver = signal(false);
}
