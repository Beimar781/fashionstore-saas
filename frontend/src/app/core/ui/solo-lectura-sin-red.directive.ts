import { Directive, ElementRef, OnDestroy, effect, inject, input } from '@angular/core';
import { MSG_NECESITA_INTERNET } from './necesita-internet.directive';
import { ToastService } from './toast.service';

/** Textos de botón que escriben en el servidor (crear, editar, activar, eliminar, subir, generar…). «Cancelar» y «Cerrar» no escriben y quedan libres. */
export const BOTON_DE_ESCRITURA = /^\s*(\+\s*)?(nuev[oa]s?|crear|editar|guardar|desactivar|activar|eliminar|quitar|suspender|reactivar|asignar|anular|subir|generar|hacer principal|inactivar|retirar|volver a|cancelar (el )?(lote|aviso)|aplicar|restablecer|enviar|confirmar|cambiar (de )?(plan|estado))/i;

/**
 * Marca como «necesita Internet» todo botón de escritura dentro de la zona (por ejemplo las pantallas del Administrador, que no tienen modo sin conexión):
 * se ven apagados, explican el motivo y, si se tocan, avisan en vez de lanzar la petición. Sirve para las pantallas que se abren después (modales incluidos).
 */
@Directive({ selector: '[soloLecturaSinRed]' })
export class SoloLecturaSinRedDirective implements OnDestroy {
  private zona = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;
  private toast = inject(ToastService);
  readonly soloLecturaSinRed = input<boolean>(false);
  private observador = new MutationObserver(() => this.marcar());
  private alTocar = (e: Event) => {
    const boton = (e.target as HTMLElement | null)?.closest('button');
    if (!this.soloLecturaSinRed() || !boton || !this.esEscritura(boton) || boton.hasAttribute('permiteSinRed')) return;
    e.stopImmediatePropagation(); e.preventDefault();
    this.toast.aviso(MSG_NECESITA_INTERNET);
  };

  constructor() {
    this.zona.addEventListener('click', this.alTocar, true);
    this.observador.observe(this.zona, { childList: true, subtree: true });
    effect(() => { this.soloLecturaSinRed(); this.marcar(); });
  }

  private esEscritura(boton: HTMLElement) { return BOTON_DE_ESCRITURA.test(boton.textContent ?? ''); }

  private marcar() {
    const activa = this.soloLecturaSinRed();
    this.observador.disconnect();  // cambiar clases no debe disparar otra vez al observador
    for (const boton of Array.from(this.zona.querySelectorAll('button'))) {
      const escribe = activa && this.esEscritura(boton) && !boton.hasAttribute('permiteSinRed');
      boton.classList.toggle('sin-internet', escribe);
      if (escribe) { boton.setAttribute('aria-disabled', 'true'); boton.title = MSG_NECESITA_INTERNET; }
      else if (boton.classList.contains('sin-internet') === false && boton.title === MSG_NECESITA_INTERNET) { boton.removeAttribute('aria-disabled'); boton.removeAttribute('title'); }
    }
    this.observador.observe(this.zona, { childList: true, subtree: true });
  }

  ngOnDestroy() { this.observador.disconnect(); this.zona.removeEventListener('click', this.alTocar, true); }
}
