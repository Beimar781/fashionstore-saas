import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { throwError } from 'rxjs';
import { API_URL } from '../api.config';
import { ConnectivityService } from './connectivity.service';

/** Con «Simular sin conexión» activo, las llamadas a la API fallan como si no hubiera red (estado 0): la app responde igual que sin Internet. */
export const simularSinConexionInterceptor: HttpInterceptorFn = (req, next) => {
  const red = inject(ConnectivityService);
  if (red.simulado() && req.url.startsWith(API_URL)) return throwError(() => new HttpErrorResponse({ url: req.url, status: 0, statusText: 'Sin conexión simulada' }));
  return next(req);
};
