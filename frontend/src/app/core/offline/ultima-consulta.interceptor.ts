import { HttpInterceptorFn, HttpResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { tap } from 'rxjs/operators';
import { API_URL } from '../api.config';
import { ConnectivityService } from './connectivity.service';
import { UltimaConsultaService } from './ultima-consulta.service';

/** Anota cuándo llegaron datos reales del servidor. Solo cuenta con conexión: una respuesta que el service worker entrega desde su caché sin red no actualiza la fecha. */
export const ultimaConsultaInterceptor: HttpInterceptorFn = (req, next) => {
  const red = inject(ConnectivityService);
  const ultima = inject(UltimaConsultaService);
  return next(req).pipe(tap((ev) => { if (ev instanceof HttpResponse && req.method === 'GET' && req.url.startsWith(API_URL) && red.online()) ultima.registrar(); }));
};
