import { Routes } from '@angular/router';

/** Tienda del Cliente (SaaS: CU-03 y CU-04). Cuelga de /tienda. */
export const TIENDA_ROUTES: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'catalogo' },
  { path: 'catalogo', loadComponent: () => import('./catalogo.page').then((m) => m.CatalogoPage), title: 'Catálogo · FashionStore' },
  { path: 'catalogo/:id', loadComponent: () => import('./prenda.page').then((m) => m.PrendaPage), title: 'Prenda · FashionStore' },
  { path: 'reservar', loadComponent: () => import('../reservas/reservar.page').then((m) => m.ReservarPage), title: 'Mi reserva · FashionStore' },
  { path: 'reservas', loadComponent: () => import('../reservas/mis-reservas.page').then((m) => m.MisReservasPage), title: 'Mis reservas · FashionStore' },
];
