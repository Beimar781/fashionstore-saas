import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { API_URL } from '../api.config';
import { AuthService } from './auth.service';

const esAuthPublica = (url: string) => url.includes('/auth/login') || url.includes('/auth/refresh');

/** Agrega el token Bearer a las peticiones a la API y, ante un 401, intenta renovar la sesión una vez. */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  if (!req.url.startsWith(API_URL) || esAuthPublica(req.url)) return next(req);

  const conToken = (r: HttpRequest<unknown>, token: string | null) =>
    token ? r.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : r;

  return next(conToken(req, auth.accessToken())).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status !== 401 || !auth.refreshToken()) return throwError(() => err);
      return auth.refrescar().pipe(
        switchMap((r) => next(conToken(req, r.access_token))),
        catchError((e) => { auth.cerrarSesion(); return throwError(() => e); }),
      );
    }),
  );
};
