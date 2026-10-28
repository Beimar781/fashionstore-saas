import { Injectable } from '@angular/core';

declare global {
  interface Window { Stripe?: (clave: string, opciones?: object) => any; }
}

/** Carga Stripe.js desde Stripe solo cuando hace falta (modo prueba). El número de la tarjeta lo captura Stripe en su propio campo:
 *  nuestro servidor y nuestro código nunca lo ven. */
@Injectable({ providedIn: 'root' })
export class StripeJsService {
  private carga?: Promise<NonNullable<Window['Stripe']>>;

  cargar(): Promise<NonNullable<Window['Stripe']>> {
    this.carga ??= new Promise((resolver, rechazar) => {
      if (window.Stripe) return resolver(window.Stripe);
      const s = document.createElement('script');
      s.src = 'https://js.stripe.com/v3/';
      s.onload = () => (window.Stripe ? resolver(window.Stripe) : rechazar(new Error('Stripe.js no está disponible.')));
      s.onerror = () => { this.carga = undefined; rechazar(new Error('No se pudo cargar Stripe.js. Revise su conexión.')); };
      document.head.appendChild(s);
    });
    return this.carga;
  }
}
