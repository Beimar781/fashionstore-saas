import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { Rol } from '../models';
import { AuthService } from './auth.service';

/** Exige sesión iniciada. */
export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  return auth.autenticado() ? true : inject(Router).parseUrl('/login');
};

/** Evita volver a la pantalla de login con sesión activa. */
export const invitadoGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  return auth.autenticado() ? inject(Router).parseUrl(auth.rutaInicial()) : true;
};

/** Restringe una sección a ciertos roles (la autorización real la aplica el backend, RNF01). */
export const rolGuard = (...roles: Rol[]): CanActivateFn => () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (!auth.autenticado()) return router.parseUrl('/login');
  return roles.includes(auth.rol()!) ? true : router.parseUrl(auth.rutaInicial());
};

/** Con suscripción no vigente el Administrador solo puede consultar su plan (RN05). */
export const operativoGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  return auth.restringido() ? inject(Router).parseUrl('/empresa/plan') : true;
};
