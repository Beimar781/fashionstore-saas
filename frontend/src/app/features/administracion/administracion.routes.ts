import { Routes } from '@angular/router';
import { operativoGuard } from '../../core/auth/auth.guards';

export const ADMINISTRACION_ROUTES: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'plan' },
  { path: 'plan', loadComponent: () => import('./mi-plan.page').then((m) => m.MiPlanPage), title: 'Mi plan · FashionStore' },
  { path: 'usuarios', canActivate: [operativoGuard], loadComponent: () => import('./usuarios.page').then((m) => m.UsuariosPage), title: 'Usuarios · FashionStore' },
  { path: 'sucursales', canActivate: [operativoGuard], loadComponent: () => import('./sucursales.page').then((m) => m.SucursalesPage), title: 'Sucursales · FashionStore' },
  { path: 'catalogo', canActivate: [operativoGuard], loadChildren: () => import('../primer-parcial/catalogo/catalogo-admin.routes').then((m) => m.CATALOGO_ADMIN_ROUTES) },
];
