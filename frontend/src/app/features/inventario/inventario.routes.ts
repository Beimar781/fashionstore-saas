import { Routes } from '@angular/router';

const inventario = () => import('./inventario.page').then((m) => m.InventarioPage);
const movimientos = () => import('./movimientos.page').then((m) => m.MovimientosPage);

/** Panel del Encargado (CU-26): inventario de su sucursal, recepción de lotes y bitácora. Cuelga de /sucursal. */
export const SUCURSAL_ROUTES: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'reservas' },
  { path: 'caja', loadComponent: () => import('../primer-parcial/ventas/caja.page').then((m) => m.CajaPage), title: 'Caja · FashionStore' },
  { path: 'ventas', loadComponent: () => import('../primer-parcial/reportes/ventas-sucursal.page').then((m) => m.VentasSucursalPage), title: 'Ventas de la sucursal · FashionStore' },
  { path: 'reservas', loadComponent: () => import('../primer-parcial/reservas/reservas-sucursal.page').then((m) => m.ReservasSucursalPage), title: 'Reservas de la sucursal · FashionStore' },
  { path: 'atencion', loadComponent: () => import('../primer-parcial/reservas/atencion.page').then((m) => m.AtencionPage), title: 'Atención de reservas · FashionStore' },
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
