import {
  HttpClient,
  HttpErrorResponse,
  provideHttpClient,
  withInterceptors,
} from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { throwError } from 'rxjs';
import { API_URL } from '../api.config';
import { AuthService } from './auth.service';
import { authInterceptor } from './auth.interceptor';

describe('authInterceptor: sesión previa', () => {
  let cliente: HttpClient;
  let http: HttpTestingController;
  let errorRenovacion: HttpErrorResponse;
  let cerrarSesion: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    errorRenovacion = new HttpErrorResponse({ status: 0, statusText: 'Network Error' });
    cerrarSesion = vi.fn();
    const auth = {
      accessToken: () => 'access-anterior',
      refreshToken: () => 'refresh-guardado',
      refrescar: () => throwError(() => errorRenovacion),
      cerrarSesion,
    } as unknown as AuthService;
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: auth },
      ],
    });
    cliente = TestBed.inject(HttpClient);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('conserva la sesión si la red cae al renovar el token', () => {
    let recibido: unknown;
    cliente.get(`${API_URL}/catalogo/sucursales`).subscribe({ error: (e) => (recibido = e) });
    http
      .expectOne(`${API_URL}/catalogo/sucursales`)
      .flush({}, { status: 401, statusText: 'Unauthorized' });
    expect(recibido).toBe(errorRenovacion);
    expect(cerrarSesion).not.toHaveBeenCalled();
  });

  it('cierra la sesión si el servidor rechaza el refresh guardado', () => {
    errorRenovacion = new HttpErrorResponse({ status: 401, statusText: 'Unauthorized' });
    cliente.get(`${API_URL}/catalogo/sucursales`).subscribe({ error: () => undefined });
    http
      .expectOne(`${API_URL}/catalogo/sucursales`)
      .flush({}, { status: 401, statusText: 'Unauthorized' });
    expect(cerrarSesion).toHaveBeenCalledOnce();
  });
});
