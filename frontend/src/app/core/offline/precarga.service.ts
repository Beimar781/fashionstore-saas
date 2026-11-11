import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, effect, inject, untracked } from '@angular/core';
import { API_URL } from '../api.config';
import { AuthService } from '../auth/auth.service';
import { ROL } from '../models';
import { ConnectivityService } from './connectivity.service';

const MINUTOS = 10;

/** Lecturas de las pantallas normales de cada rol. Al iniciar sesión y al volver la red se piden en segundo plano: el interceptor de lecturas las guarda y quedan disponibles sin conexión. */
/** Fecha de hoy como la usan las pantallas de ventas (aaaa-mm-dd, hora local). */
export function hoyLocal(ahora = new Date()): string {
  const d = (n: number) => String(n).padStart(2, '0');
  return `${ahora.getFullYear()}-${d(ahora.getMonth() + 1)}-${d(ahora.getDate())}`;
}

export function rutasDePrecarga(rol: string): { ruta: string; params?: Record<string, string> }[] {
  switch (rol) {
    case ROL.CLIENTE: return [
      { ruta: '/catalogo/sucursales' }, { ruta: '/carrito' }, { ruta: '/compras' }, { ruta: '/reservas' }, { ruta: '/pagos/tarjetas' },
      { ruta: '/categorias' }, { ruta: '/marcas' }, { ruta: '/colores' }, { ruta: '/grupos-talla' },
      { ruta: '/catalogo/buscar', params: { orden: 'recientes', pagina: '1' } },
    ];
    case ROL.CAJERO: return [
      { ruta: '/reservas-sucursal' }, { ruta: '/devoluciones/configuracion' }, { ruta: '/devoluciones' }, { ruta: '/caja/ventas/pendientes' },
      { ruta: '/reportes/sucursal/resumen', params: { fecha: hoyLocal() } }, { ruta: '/reportes/sucursal/ventas', params: { desde: hoyLocal(), hasta: hoyLocal() } },
    ];
    case ROL.ENCARGADO: return [
      { ruta: '/reservas-sucursal' }, { ruta: '/inventario/sucursal', params: { pagina: '1' } }, { ruta: '/inventario/recepciones' },
      { ruta: '/offline/conflictos' }, { ruta: '/devoluciones/configuracion' }, { ruta: '/devoluciones' },
      { ruta: '/reportes/sucursal/resumen', params: { fecha: hoyLocal() } }, { ruta: '/reportes/sucursal/ventas', params: { desde: hoyLocal(), hasta: hoyLocal() } },
    ];
    case ROL.PROVEEDOR: return [
      { ruta: '/abastecimiento/mi-proveedor' }, { ruta: '/abastecimiento/resumen' }, { ruta: '/abastecimiento/lotes' }, { ruta: '/abastecimiento/propuestas' },
      { ruta: '/abastecimiento/sucursales' }, { ruta: '/abastecimiento/variantes', params: { q: '' } },
    ];
    case ROL.ADMIN: return [
      { ruta: '/usuarios' }, { ruta: '/sucursales' }, { ruta: '/mi-plan' }, { ruta: '/productos', params: { pagina: '1' } }, { ruta: '/inventario/global', params: { pagina: '1' } },
      { ruta: '/proveedores' }, { ruta: '/ia/reportes' }, { ruta: '/categorias' }, { ruta: '/promociones' }, { ruta: '/offline/conflictos' },
      { ruta: '/abastecimiento/resumen' }, { ruta: '/abastecimiento/lotes' }, { ruta: '/abastecimiento/propuestas' }, { ruta: '/abastecimiento/sucursales' },
      { ruta: '/devoluciones/configuracion' }, { ruta: '/devoluciones' }, { ruta: '/reportes/indicadores', params: { dias: '30' } },
      { ruta: '/temporadas' }, { ruta: '/colecciones' }, { ruta: '/marcas' }, { ruta: '/colores' }, { ruta: '/grupos-talla' },
    ];
    default: return [];
  }
}

@Injectable({ providedIn: 'root' })
export class PrecargaService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private red = inject(ConnectivityService);
  private ultima = 0;

  constructor() {
    effect(() => {
      const s = this.auth.sesion();
      if (s && this.red.online()) untracked(() => this.precargar());
    });
  }

  /** Pide las lecturas del rol, como mucho una vez cada 10 minutos. Un fallo se ignora: la pantalla igual carga cuando se abra. */
  precargar(forzar = false) {
    const s = this.auth.sesion();
    if (!s || (!forzar && Date.now() - this.ultima < MINUTOS * 60_000)) return;
    this.ultima = Date.now();
    for (const { ruta, params } of rutasDePrecarga(s.usuario.rol)) {
      this.http.get(`${API_URL}${ruta}`, { params: new HttpParams({ fromObject: params ?? {} }) }).subscribe({ error: () => undefined });
    }
  }
}
