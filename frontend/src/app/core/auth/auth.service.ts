import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, finalize, shareReplay, tap } from 'rxjs';
import { API_URL } from '../api.config';
import { LoginBody, ROL, Rol, Sesion, TokenResponse } from '../models';
import { LocalDbService } from '../offline/local-db.service';

const K_ACCESS = 'fs.access', K_REFRESH = 'fs.refresh', K_SESION = 'fs.sesion';

/** CU-02 · Sesión con contexto de empresa. Los tokens y el contexto se guardan localmente (paso 8)
 *  para poder seguir operando sin conexión. */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  private local = inject(LocalDbService);

  readonly sesion = signal<Sesion | null>(this.leer());
  readonly autenticado = computed(() => this.sesion() !== null);
  readonly rol = computed<Rol | null>(() => this.sesion()?.usuario.rol ?? null);
  readonly restringido = computed(() => this.sesion()?.restringido ?? false);

  private refrescando$: Observable<TokenResponse> | null = null;

  accessToken(): string | null { return localStorage.getItem(K_ACCESS); }
  refreshToken(): string | null { return localStorage.getItem(K_REFRESH); }

  /** CU-01 · Registro de cliente: la cuenta queda creada y la sesión iniciada. */
  registrarCliente(body: { codigo_empresa: string; nombre: string; apellidos: string; email: string; password: string }): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${API_URL}/auth/registro`, body).pipe(tap((r) => this.guardar(r)));
  }

  olvidePassword(body: { codigo_empresa: string | null; email: string }): Observable<{ detail: string }> {
    return this.http.post<{ detail: string }>(`${API_URL}/auth/olvide-password`, body);
  }

  restablecerPassword(body: { token: string; password: string }): Observable<{ detail: string }> {
    return this.http.post<{ detail: string }>(`${API_URL}/auth/restablecer-password`, body);
  }

  login(body: LoginBody): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${API_URL}/auth/login`, body).pipe(tap((r) => this.guardar(r)));
  }

  /** Renueva el token; varias peticiones 401 simultáneas comparten una sola renovación. */
  refrescar(): Observable<TokenResponse> {
    this.refrescando$ ??= this.http
      .post<TokenResponse>(`${API_URL}/auth/refresh`, { refresh_token: this.refreshToken() })
      .pipe(tap((r) => this.guardar(r)), finalize(() => (this.refrescando$ = null)), shareReplay(1));
    return this.refrescando$;
  }

  /** Recupera el contexto actual (por ejemplo, después de que el SuperAdministrador cambie el plan). */
  actualizarSesion(): Observable<Sesion> {
    return this.http.get<Sesion>(`${API_URL}/auth/me`).pipe(
      tap((s) => { localStorage.setItem(K_SESION, JSON.stringify(s)); this.sesion.set(s); void this.local.guardarSesion(s); }),
    );
  }

  tieneSesionLocal(email: string, codigo: string | null): boolean {
    const s = this.sesion();
    if (!s || !this.refreshToken()) return false;
    const mismoCodigo = (s.empresa?.codigo ?? '').toLowerCase() === (codigo ?? '').trim().toLowerCase();
    return s.usuario.email.toLowerCase() === email.trim().toLowerCase() && mismoCodigo;
  }

  cerrarSesion(): void {
    // se avisa al servidor para que quede en la bitácora; si no hay conexión, igual se cierra la sesión local
    if (this.sesion()) this.http.post(`${API_URL}/auth/logout`, {}).subscribe({ error: () => undefined });
    localStorage.removeItem(K_ACCESS); localStorage.removeItem(K_REFRESH); localStorage.removeItem(K_SESION);
    this.sesion.set(null);
    void this.local.borrarSesion();
    void this.router.navigateByUrl('/login');
  }

  /** Panel al que se redirige según el rol (CU-02, paso 7). */
  rutaInicial(): string {
    const s = this.sesion();
    if (!s) return '/login';
    switch (s.usuario.rol) {
      case ROL.SUPER: return '/plataforma/empresas';
      case ROL.ADMIN: return s.restringido ? '/empresa/plan' : '/empresa/plan';
      case ROL.ENCARGADO: return '/sucursal';
      case ROL.CAJERO: return '/pos';
      case ROL.PROVEEDOR: return '/proveedor';
      default: return '/tienda';
    }
  }

  private guardar(r: TokenResponse): void {
    const { access_token, refresh_token, token_type, ...sesion } = r;
    void token_type;
    localStorage.setItem(K_ACCESS, access_token);
    localStorage.setItem(K_REFRESH, refresh_token);
    localStorage.setItem(K_SESION, JSON.stringify(sesion));
    this.sesion.set(sesion);
    void this.local.guardarSesion(sesion);
  }

  private leer(): Sesion | null {
    try { return JSON.parse(localStorage.getItem(K_SESION) ?? 'null'); } catch { return null; }
  }
}
