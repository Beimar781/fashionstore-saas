import { Routes } from '@angular/router';

/** Administración del catálogo (primer parcial, CU-16 a CU-19). Cuelga de /empresa/catalogo. */
export const CATALOGO_ADMIN_ROUTES: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'productos' },
  { path: 'atributos', loadComponent: () => import('./atributos.page').then((m) => m.AtributosPage), title: 'Categorías, tallas y colores · FashionStore' },
  { path: 'temporadas', loadComponent: () => import('./temporadas.page').then((m) => m.TemporadasPage), title: 'Temporadas y colecciones · FashionStore' },
  { path: 'productos', loadComponent: () => import('./productos.page').then((m) => m.ProductosPage), title: 'Productos · FashionStore' },
  { path: 'productos/:id', loadComponent: () => import('./producto-detalle.page').then((m) => m.ProductoDetallePage), title: 'Producto · FashionStore' },
  { path: 'promociones', loadComponent: () => import('./promociones.page').then((m) => m.PromocionesPage), title: 'Promociones · FashionStore' },
];
