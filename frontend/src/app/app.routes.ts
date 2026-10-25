import { Routes } from '@angular/router';
import { authGuard, invitadoGuard, rolGuard } from './core/auth/auth.guards';
import { ROL } from './core/models';

/** Un módulo (carga diferida) por paquete de casos de uso: auth, plataforma y administración. */
export const routes: Routes = [
  { path: 'login', canActivate: [invitadoGuard], loadComponent: () => import('./features/auth/login.page').then((m) => m.LoginPage), title: 'Iniciar sesión · FashionStore' },
  { path: 'olvide-password', canActivate: [invitadoGuard], loadComponent: () => import('./features/auth/olvide-password.page').then((m) => m.OlvidePasswordPage), title: 'Recuperar contraseña · FashionStore' },
  { path: 'restablecer-password', loadComponent: () => import('./features/auth/restablecer-password.page').then((m) => m.RestablecerPasswordPage), title: 'Nueva contraseña · FashionStore' },
  {
    path: 'plataforma',
    canActivate: [rolGuard(ROL.SUPER)],
    loadComponent: () => import('./layout/shell.component').then((m) => m.ShellComponent),
    loadChildren: () => import('./features/plataforma/plataforma.routes').then((m) => m.PLATAFORMA_ROUTES),
  },
  {
    path: 'empresa',
    canActivate: [rolGuard(ROL.ADMIN)],
    loadComponent: () => import('./layout/shell.component').then((m) => m.ShellComponent),
    loadChildren: () => import('./features/administracion/administracion.routes').then((m) => m.ADMINISTRACION_ROUTES),
  },
  // Paneles de los demás roles (se completan en el Lote 2)
  ...['sucursal', 'pos', 'tienda'].map((path) => ({
    path, canActivate: [authGuard],
    loadComponent: () => import('./features/panel-pendiente.page').then((m) => m.PanelPendientePage),
  })),
  { path: '', pathMatch: 'full', redirectTo: 'login' },
  { path: '**', redirectTo: 'login' },
];
