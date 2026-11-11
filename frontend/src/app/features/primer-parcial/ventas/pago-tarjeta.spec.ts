import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ComprasApi } from '../../../core/api/compras.api';
import { StripeJsService } from '../../../core/pagos/stripe-js.service';
import { PagoTarjetaComponent } from './pago-tarjeta.component';

const cfg = { modo: 'stripe', publishable_key: 'pk_test_x', tarjetas_prueba: [] };
const inicio = { modo: 'stripe', pago_id: 9, client_secret: 'cs_x', publishable_key: 'pk_test_x' };

describe('Pago con tarjeta nueva en Stripe', () => {
  let confirmarCard = vi.fn();
  const confirmarPago = vi.fn(() => throwError(() => ({ status: 402, error: { mensaje: 'Pago rechazado' } })));

  async function montar() {
    TestBed.resetTestingModule();
    const stripe = { elements: () => ({ create: () => ({ mount: (s: string) => document.querySelector(s)!.appendChild(document.createElement('iframe')), destroy: () => undefined }) }), confirmCardPayment: confirmarCard };
    TestBed.configureTestingModule({
      providers: [
        { provide: ComprasApi, useValue: { configPago: () => of(cfg), tarjetas: () => of([]), iniciarPago: () => of(inicio), confirmarPago } },
        { provide: StripeJsService, useValue: { cargar: async () => () => stripe } },
      ],
    });
    const fixture = TestBed.createComponent(PagoTarjetaComponent);
    fixture.componentRef.setInput('total', '100.00');
    fixture.componentRef.setInput('pedidoId', 1);
    fixture.detectChanges();
    await new Promise((r) => setTimeout(r, 120));
    fixture.detectChanges();
    return fixture;
  }

  beforeEach(() => { confirmarCard = vi.fn(); confirmarPago.mockClear(); });

  it('el campo de Stripe sigue en el DOM mientras se procesa el pago', async () => {
    let terminar!: (v: unknown) => void;
    confirmarCard.mockReturnValue(new Promise((r) => (terminar = r)));
    const f = await montar();
    const campo = f.nativeElement.querySelector('#tarjeta-stripe');
    expect(campo).toBeTruthy();
    f.componentInstance.pagar();
    f.detectChanges();
    expect(f.componentInstance.fase()).toBe('procesando');
    expect(f.nativeElement.querySelector('#tarjeta-stripe')).toBe(campo);
    expect(campo.hasChildNodes()).toBe(true);
    terminar({ error: undefined });
  });

  it('un error de Stripe.js (campo vacío o sin montar) no se muestra como rechazo bancario ni llama al servidor', async () => {
    confirmarCard.mockResolvedValue({ error: { type: 'validation_error', message: 'Your card number is incomplete.' } });
    const f = await montar();
    f.componentInstance.pagar();
    await new Promise((r) => setTimeout(r, 10));
    f.detectChanges();
    expect(confirmarPago).not.toHaveBeenCalled();
    expect(f.componentInstance.fase()).toBe('error');
    expect(f.nativeElement.textContent).toContain('Revise los datos de la tarjeta');
    expect(f.nativeElement.textContent).not.toContain('Pago rechazado');
  });

  it('un rechazo real del banco (card_error) sí se confirma en el servidor y se muestra como rechazado', async () => {
    confirmarCard.mockResolvedValue({ error: { type: 'card_error', message: 'Your card was declined.' } });
    const f = await montar();
    f.componentInstance.pagar();
    await new Promise((r) => setTimeout(r, 10));
    f.detectChanges();
    expect(confirmarPago).toHaveBeenCalled();
    expect(f.componentInstance.fase()).toBe('rechazado');
    expect(f.nativeElement.textContent).toContain('Pago rechazado');
  });
});
