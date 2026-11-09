import { Pipe, PipeTransform } from '@angular/core';

/** Formato único del dinero en toda la web: «Bs 1.250,50» (punto de miles, coma decimal). Todo el sistema opera solo en bolivianos. */
export function formatoBs(valor: unknown): string {
  if (valor === null || valor === undefined || valor === '') return '';
  const numero = Number(valor);
  if (!Number.isFinite(numero)) return String(valor);
  const [entero, decimales] = Math.abs(numero).toFixed(2).split('.');
  return `${numero < 0 ? '-' : ''}Bs ${entero.replace(/\B(?=(\d{3})+(?!\d))/g, '.')},${decimales}`;
}

@Pipe({ name: 'bs' })
export class BsPipe implements PipeTransform {
  transform(valor: unknown): string { return formatoBs(valor); }
}
