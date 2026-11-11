import { Injectable, inject } from '@angular/core';
import { ComprasApi } from '../api/compras.api';
import { AuthService } from '../auth/auth.service';
import { TarjetaGuardada } from '../compras.models';
import { LocalDbService } from '../offline/local-db.service';

/**
 * Tarjetas guardadas del Cliente (solo marca, últimos 4 y vencimiento; nunca el número). Una sola copia local para comprar sin conexión con una tarjeta guardada.
 * La copia se actualiza al iniciar sesión, al volver la red, al guardar una tarjeta (pago con «Guardar esta tarjeta») y al eliminarla.
 */
@Injectable({ providedIn: 'root' })
export class TarjetasGuardadasService {
  private api = inject(ComprasApi);
  private db = inject(LocalDbService);
  private auth = inject(AuthService);

  private get clave() { const s = this.auth.sesion(); return `${s?.empresa?.id ?? 0}:${s?.usuario.id ?? 0}`; }

  /** Con red: pide la lista al servidor y la deja guardada. Devuelve null si no hubo respuesta (se conserva la copia anterior). */
  async refrescar(): Promise<TarjetaGuardada[] | null> {
    try {
      const lista = await new Promise<TarjetaGuardada[]>((ok, mal) => this.api.tarjetas().subscribe({ next: ok, error: mal }));
      await this.guardarCopia(lista);
      return lista;
    } catch { return null; }
  }

  guardarCopia(lista: TarjetaGuardada[]) { return this.db.guardarTarjetasLocal(this.clave, lista); }
  async locales(): Promise<TarjetaGuardada[]> { return (await this.db.leerTarjetasLocal<TarjetaGuardada[]>(this.clave)) ?? []; }

  /** Una tarjeta eliminada ya no se ofrece sin conexión. */
  async quitar(id: number) { await this.guardarCopia((await this.locales()).filter((t) => t.id !== id)); }
}
