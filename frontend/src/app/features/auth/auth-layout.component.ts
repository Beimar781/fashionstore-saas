import { Component } from '@angular/core';

/** Marco común de las pantallas de acceso (inicio de sesión y recuperación de contraseña). */
@Component({
  selector: 'app-auth-layout',
  template: `
    <main class="wrap">
      <section class="hero" aria-hidden="true">
        <div class="mark">F</div>
        <h1>FashionStore</h1>
        <p>Plataforma SaaS para cadenas de tiendas de ropa. Cada empresa, su propio espacio.</p>
      </section>
      <section class="panel card"><ng-content /></section>
    </main>`,
  styles: `
    .wrap { min-height: 100vh; display: grid; grid-template-columns: 1.1fr 1fr; }
    .hero { background: var(--side); color: #fff; padding: 4rem; display: flex; flex-direction: column; justify-content: center; gap: 1rem;
      background-image: radial-gradient(circle at 20% 15%, rgba(122,31,61,.55), transparent 55%); }
    .mark { width: 56px; height: 56px; border-radius: 14px; background: var(--accent); display: grid; place-items: center; font: 600 2rem var(--serif); }
    .hero h1 { font-size: 2.6rem; } .hero p { color: #cfc8d8; max-width: 34ch; font-size: 1.05rem; }
    .panel { align-self: center; justify-self: center; width: min(420px, calc(100% - 2rem)); padding: 2rem; display: grid; gap: .9rem; margin: 2rem 0; }
    @media (max-width: 820px) { .wrap { grid-template-columns: 1fr; } .hero { padding: 1.5rem; } .hero h1 { font-size: 1.8rem; } .hero p { display: none; } .panel { margin: 1.25rem auto; } }`,
})
export class AuthLayoutComponent {}
