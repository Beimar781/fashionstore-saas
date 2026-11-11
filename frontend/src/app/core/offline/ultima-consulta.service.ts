import { Injectable, signal } from '@angular/core';

const CLAVE = 'fs.ultima_consulta';

/** Cuándo se recibieron por última vez datos del servidor (con conexión real). Sin red, las pantallas del Administrador muestran lo último que vieron con esta fecha («Datos al…»). */
@Injectable({ providedIn: 'root' })
export class UltimaConsultaService {
  readonly momento = signal<string | null>(this.leer());

  registrar() {
    const ahora = new Date().toISOString();
    this.momento.set(ahora);
    try { localStorage.setItem(CLAVE, ahora); } catch { /* sin almacenamiento: queda solo en memoria */ }
  }

  /** Al cerrar sesión: los datos guardados eran de esa cuenta. */
  olvidar() {
    this.momento.set(null);
    try { localStorage.removeItem(CLAVE); } catch { /* nada que borrar */ }
  }

  private leer(): string | null {
    try { return localStorage.getItem(CLAVE); } catch { return null; }
  }
}
