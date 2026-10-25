import { Routes } from '@angular/router';

export const PLATAFORMA_ROUTES: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'empresas' },
  { path: 'empresas', loadComponent: () => import('./empresas.page').then((m) => m.EmpresasPage), title: 'Empresas · FashionStore' },
  { path: 'empresas/:id/suscripcion', loadComponent: () => import('./suscripcion.page').then((m) => m.SuscripcionPage), title: 'Suscripción · FashionStore' },
  { path: 'planes', loadComponent: () => import('./planes.page').then((m) => m.PlanesPage), title: 'Planes · FashionStore' },
];
