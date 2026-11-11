import { Injectable, inject, signal } from '@angular/core';
import { AuthService } from '../auth/auth.service';
import { LocalDbService } from './local-db.service';

/** Rutas que nunca se guardan: la sesión, lo que genera la IA, las notificaciones y las descargas pesadas que ya tienen su propio almacén. */
const EXCLUIDAS = ['/auth/', '/asistente', '/vestidor', '/notificaciones', '/offline/catalogo', '/pagos/config'];
const MAXIMO = 400;

/** E1 · Copia de las lecturas (GET) hechas con red. Sin red, el mismo GET se responde con la última copia de ESA cuenta, con su fecha («Datos al…»). */
@Injectable({ providedIn: 'root' })
export class LecturasLocalesService {
  private db = inject(LocalDbService);
  private auth = inject(AuthService);
  private guardadas = 0;
  /** Fecha de la última lectura entregada desde la copia (la pantalla puede mostrar «Datos al…»). */
  readonly datosLocalesDesde = signal<string | null>(null);

  puedeGuardar(url: string): boolean { return !EXCLUIDAS.some((e) => url.includes(e)); }

  private clave(urlConFiltros: string): string {
    const s = this.auth.sesion();
    return `${s?.empresa?.id ?? 0}:${s?.usuario.id ?? 0}|${urlConFiltros}`;
  }

  async guardar(urlConFiltros: string, cuerpo: unknown): Promise<void> {
    if (!this.auth.sesion()) return;
    await this.db.guardarLectura({ clave: this.clave(urlConFiltros), cuerpo, fecha: new Date().toISOString() });
    if (++this.guardadas % 25 === 0) await this.db.podarLecturas(MAXIMO);
  }

  async leer(urlConFiltros: string) { return this.auth.sesion() ? this.db.leerLectura(this.clave(urlConFiltros)) : undefined; }

  /** Al cerrar sesión: las lecturas eran de esa cuenta. */
  async olvidar(): Promise<void> { this.datosLocalesDesde.set(null); await this.db.borrarLecturas(); }
}
