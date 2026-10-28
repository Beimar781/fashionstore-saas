import { Routes } from '@angular/router';

const inventario = () => import('./inventario.page').then((m) => m.InventarioPage);
const movimientos = () => import('./movimientos.page').then((m) => m.MovimientosPage);

/** Panel del Encargado (CU-26): inventario de su sucursal, recepción de lotes y bitácora. Cuelga de /sucursal. */
export const SUCURSAL_ROUTES: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'inventario' },
  { path: 'inventario', loadComponent: inventario, title: 'Inventario de la sucursal · FashionStore' },
  { path: 'recepciones', loadComponent: () => import('./recepciones.page').then((m) => m.RecepcionesPage), title: 'Recepción de mercadería · FashionStore' },
  { path: 'movimientos', loadComponent: movimientos, title: 'Movimientos · FashionStore' },
];

/** Inventario del Administrador (CU-20). Cuelga de /empresa/inventario. */
export const INVENTARIO_ADMIN_ROUTES: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'global' },
  { path: 'global', loadComponent: inventario, title: 'Inventario global · FashionStore' },
  { path: 'movimientos', loadComponent: movimientos, title: 'Movimientos · FashionStore' },
];
