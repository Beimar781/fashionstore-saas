import { Routes } from '@angular/router';

/** Tienda del Cliente (SaaS: CU-03 y CU-04). Cuelga de /tienda. */
export const TIENDA_ROUTES: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'catalogo' },
  { path: 'catalogo', loadComponent: () => import('./catalogo.page').then((m) => m.CatalogoPage), title: 'Catálogo · FashionStore' },
  { path: 'catalogo/:id', loadComponent: () => import('./prenda.page').then((m) => m.PrendaPage), title: 'Prenda · FashionStore' },
  { path: 'offline', loadComponent: () => import('../offline/modo-offline.page').then((m) => m.ModoOfflinePage), title: 'Modo sin conexión · FashionStore' },
  { path: 'asistente', loadComponent: () => import('../primer-parcial/ia/asistente.page').then((m) => m.AsistentePage), title: 'Asistente · FashionStore' },
  { path: 'reservar', loadComponent: () => import('../reservas/reservar.page').then((m) => m.ReservarPage), title: 'Mi reserva · FashionStore' },
  { path: 'reservas', loadComponent: () => import('../reservas/mis-reservas.page').then((m) => m.MisReservasPage), title: 'Mis reservas · FashionStore' },
  { path: 'carrito', loadComponent: () => import('../primer-parcial/reservas/carrito.page').then((m) => m.CarritoPage), title: 'Mi carrito · FashionStore' },
  { path: 'checkout', loadComponent: () => import('../primer-parcial/ventas/checkout.page').then((m) => m.CheckoutPage), title: 'Pagar · FashionStore' },
  { path: 'compras', loadComponent: () => import('../primer-parcial/ventas/mis-compras.page').then((m) => m.MisComprasPage), title: 'Mis compras · FashionStore' },
  { path: 'compras/:id', loadComponent: () => import('../primer-parcial/ventas/compra-detalle.page').then((m) => m.CompraDetallePage), title: 'Mi compra · FashionStore' },
];
