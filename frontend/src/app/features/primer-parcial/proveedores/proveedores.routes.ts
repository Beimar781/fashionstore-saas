import { Routes } from '@angular/router';

const abastecimiento = () => import('./abastecimiento.page').then((m) => m.AbastecimientoPage);

/** Proveedores (CU-15) y abastecimiento (CU-31) del Administrador. Cuelgan de /empresa. */
export const PROVEEDORES_ADMIN_ROUTES: Routes = [
  { path: 'proveedores', loadComponent: () => import('./proveedores.page').then((m) => m.ProveedoresPage), title: 'Proveedores · FashionStore' },
  { path: 'abastecimiento', loadComponent: abastecimiento, title: 'Abastecimiento · FashionStore' },
];

/** Portal del Proveedor (CU-31). Cuelga de /proveedor. */
export const PORTAL_PROVEEDOR_ROUTES: Routes = [
  { path: '', loadComponent: abastecimiento, title: 'Mis envíos y propuestas · FashionStore' },
];
