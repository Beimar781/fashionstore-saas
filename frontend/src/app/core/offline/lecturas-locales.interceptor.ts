import { HttpErrorResponse, HttpEvent, HttpHeaders, HttpInterceptorFn, HttpResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Observable, catchError, from, of, switchMap, tap, throwError } from 'rxjs';
import { API_URL } from '../api.config';
import { ConnectivityService } from './connectivity.service';
import { LecturasLocalesService } from './lecturas-locales.service';

/**
 * E1 · Guarda cada GET de la API hecho con red y, sin red (también con «Simular sin conexión», que corta con estado 0), responde con esa copia.
 * Va ANTES del interceptor de simulación para que la simulación y el modo avión real se comporten igual.
 */
export const lecturasLocalesInterceptor: HttpInterceptorFn = (req, next) => {
  const lecturas = inject(LecturasLocalesService);
  const red = inject(ConnectivityService);
  if (req.method !== 'GET' || !req.url.startsWith(API_URL) || req.responseType !== 'json' || !lecturas.puedeGuardar(req.url)) return next(req);

  return next(req).pipe(
    tap((ev) => {
      if (ev instanceof HttpResponse && ev.status === 200 && ev.body !== null && red.online() && !ev.headers.has('X-Datos-Locales') && !(ev.headers.get('Cache-Control') ?? '').includes('no-store')) void lecturas.guardar(req.urlWithParams, ev.body);
    }),
    catchError((err: HttpErrorResponse): Observable<HttpEvent<unknown>> => {
      const sinRed = err.status === 0 || (err.status === 504 && !red.online());
      if (!sinRed) return throwError(() => err);
      return from(lecturas.leer(req.urlWithParams)).pipe(
        switchMap((copia) => {
          if (!copia) { lecturas.falloSinCopia.set(true); return throwError(() => err); }
          lecturas.datosLocalesDesde.set(copia.fecha);
          return of(new HttpResponse({ body: copia.cuerpo, status: 200, url: req.url, headers: new HttpHeaders({ 'X-Datos-Locales': copia.fecha }) }));
        }),
      );
    }),
  );
};
