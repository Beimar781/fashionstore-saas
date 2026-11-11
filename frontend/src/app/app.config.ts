import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { ApplicationConfig, isDevMode, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter, withComponentInputBinding, withNavigationErrorHandler } from '@angular/router';
import { provideServiceWorker } from '@angular/service-worker';
import { authInterceptor } from './core/auth/auth.interceptor';
import { lecturasLocalesInterceptor } from './core/offline/lecturas-locales.interceptor';
import { simularSinConexionInterceptor } from './core/offline/simular-sin-conexion.interceptor';
import { ultimaConsultaInterceptor } from './core/offline/ultima-consulta.interceptor';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    // §5.2: sin red y con una ruta que no está en caché (su módulo no se pudo cargar), se muestra la página de respaldo en vez de una pantalla en blanco
    provideRouter(routes, withComponentInputBinding(), withNavigationErrorHandler(() => { if (!navigator.onLine) window.location.assign('/sin-conexion.html'); })),
    provideHttpClient(withInterceptors([lecturasLocalesInterceptor, simularSinConexionInterceptor, authInterceptor, ultimaConsultaInterceptor])),
    // PWA: el Service Worker se registra solo en la compilación de producción (ng build)
    provideServiceWorker('sw-sync.js', { enabled: !isDevMode(), registrationStrategy: 'registerWhenStable:30000' }),
  ],
};
