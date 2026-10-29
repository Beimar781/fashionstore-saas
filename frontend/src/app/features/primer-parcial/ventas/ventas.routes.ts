import { Routes } from '@angular/router';

/** Panel del Cajero (CU-28, CU-29, CU-30). Cuelga de /pos. */
export const CAJA_ROUTES: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'caja' },
  { path: 'caja', loadComponent: () => import('./caja.page').then((m) => m.CajaPage), title: 'Caja · FashionStore' },
  { path: 'offline', loadComponent: () => import('../../offline/modo-offline.page').then((m) => m.ModoOfflinePage), title: 'Modo sin conexión · FashionStore' },
  { path: 'devoluciones', loadComponent: () => import('../../ventas/devoluciones.page').then((m) => m.DevolucionesPage), title: 'Devoluciones y cambios · FashionStore' },
];
