import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { beforeEach, describe, expect, it } from 'vitest';
import { API_URL } from '../api.config';
import { AuthService } from '../auth/auth.service';
import { LecturaLocal, LocalDbService } from './local-db.service';
import { ConnectivityService } from './connectivity.service';
import { lecturasLocalesInterceptor } from './lecturas-locales.interceptor';
import { simularSinConexionInterceptor } from './simular-sin-conexion.interceptor';
import { CarritoEstadoService } from '../carrito/carrito-estado.service';
import { ComprasApi } from '../api/compras.api';
import { CatalogoLocalService } from './catalogo-local.service';
import { ColaOperacionesService } from './cola-operaciones.service';
import { ToastService } from '../ui/toast.service';
import { Carrito } from '../compras.models';
import { rutasDePrecarga } from './precarga.service';
import { LecturasLocalesService } from './lecturas-locales.service';
import { CargandoComponent, MSG_SIN_DATOS_SIN_RED, VacioComponent } from '../ui/vacio.component';

describe('Lecturas guardadas (E1)', () => {
  const lecturas = new Map<string, LecturaLocal>();
  const online = signal(true);
  const simulado = signal(false);
  const usuario = signal(5);
  let http: HttpClient;
  let control: HttpTestingController;

  const traer = (url: string) => { let r: { cuerpo?: unknown; error?: number } = {}; http.get(`${API_URL}${url}`).subscribe({ next: (b) => (r = { cuerpo: b }), error: (e) => (r = { error: e.status }) }); return () => r; };
  const esperar = () => new Promise((ok) => setTimeout(ok, 5));

  beforeEach(() => {
    lecturas.clear(); online.set(true); simulado.set(false); usuario.set(5);
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([lecturasLocalesInterceptor, simularSinConexionInterceptor])), provideHttpClientTesting(),
        { provide: ConnectivityService, useValue: { online, simulado } },
        { provide: AuthService, useValue: { sesion: () => ({ empresa: { id: 1 }, usuario: { id: usuario() } }) } },
        { provide: LocalDbService, useValue: {
          guardarLectura: async (l: LecturaLocal) => { lecturas.set(l.clave, l); }, leerLectura: async (k: string) => lecturas.get(k),
          borrarLecturas: async () => lecturas.clear(), podarLecturas: async () => undefined } },
      ],
    });
    http = TestBed.inject(HttpClient); control = TestBed.inject(HttpTestingController);
  });

  it('con red guarda la respuesta y, con la simulación, el mismo GET sale de la copia con su fecha', async () => {
    traer('/reservas-sucursal?estado=PENDIENTE');
    control.expectOne(`${API_URL}/reservas-sucursal?estado=PENDIENTE`).flush([{ id: 1 }]);
    await esperar();
    simulado.set(true); online.set(false);
    const r = traer('/reservas-sucursal?estado=PENDIENTE');
    await esperar();
    expect(r().cuerpo).toEqual([{ id: 1 }]);
    control.expectNone(`${API_URL}/reservas-sucursal?estado=PENDIENTE`);
  });

  it('con modo avión real (estado 0 desde el navegador) también responde con la copia, y sin copia falla con estado 0', async () => {
    traer('/inventario/recepciones'); control.expectOne(`${API_URL}/inventario/recepciones`).flush([{ id: 9 }]); await esperar();
    online.set(false);
    const hay = traer('/inventario/recepciones'); control.expectOne(`${API_URL}/inventario/recepciones`).error(new ProgressEvent('error'), { status: 0 }); await esperar();
    expect(hay().cuerpo).toEqual([{ id: 9 }]);
    const noHay = traer('/inventario/otra'); control.expectOne(`${API_URL}/inventario/otra`).error(new ProgressEvent('error'), { status: 0 }); await esperar();
    expect(noHay().error).toBe(0);
  });

  it('no guarda login, IA generativa, notificaciones ni la descarga del catálogo, y un error del servidor no se disfraza', async () => {
    for (const ruta of ['/auth/me', '/asistente/outfit', '/notificaciones', '/offline/catalogo']) { traer(ruta); control.expectOne(`${API_URL}${ruta}`).flush({ x: 1 }); }
    await esperar();
    expect(lecturas.size).toBe(0);
    traer('/reservas'); control.expectOne(`${API_URL}/reservas`).flush([], { status: 200, statusText: 'OK' }); await esperar();
    const r = traer('/reservas'); control.expectOne(`${API_URL}/reservas`).flush({ detail: 'x' }, { status: 403, statusText: 'No' }); await esperar();
    expect(r().error).toBe(403);
  });

  it('las copias son de cada cuenta: otro usuario no ve las de quien salió', async () => {
    traer('/usuarios'); control.expectOne(`${API_URL}/usuarios`).flush([{ id: 1 }]); await esperar();
    usuario.set(6); online.set(false);
    const r = traer('/usuarios'); control.expectOne(`${API_URL}/usuarios`).error(new ProgressEvent('error'), { status: 0 }); await esperar();
    expect(r().error).toBe(0);
  });

  it('las rutas de precarga existen para cada rol y el rol desconocido no precarga nada', () => {
    expect(rutasDePrecarga('Cliente').map((x) => x.ruta)).toContain('/carrito');
    expect(rutasDePrecarga('Cajero').map((x) => x.ruta)).toContain('/devoluciones/configuracion');
    expect(rutasDePrecarga('Encargado').map((x) => x.ruta)).toContain('/inventario/recepciones');
    expect(rutasDePrecarga('Proveedor').map((x) => x.ruta)).toContain('/abastecimiento/lotes');
    expect(rutasDePrecarga('Administrador').map((x) => x.ruta)).toContain('/usuarios');
    expect(rutasDePrecarga('SuperAdministrador')).toEqual([]);
  });
});

describe('Estados de pantalla sin conexión (E1)', () => {
  const online = signal(false);
  const falloSinCopia = signal(false);
  beforeEach(() => {
    online.set(false); falloSinCopia.set(false); TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [{ provide: ConnectivityService, useValue: { online } }, { provide: LecturasLocalesService, useValue: { falloSinCopia } }] });
  });

  it('F · sin conexión: si la consulta no tenía copia guardada dice «necesita Internet»; si la lista vacía vino de la copia, dice lo real', () => {
    const f = TestBed.createComponent(VacioComponent); f.detectChanges();
    expect((f.nativeElement as HTMLElement).textContent).not.toContain(MSG_SIN_DATOS_SIN_RED);  // vacío real guardado: no se afirma que falten datos
    falloSinCopia.set(true); f.detectChanges();
    expect((f.nativeElement as HTMLElement).textContent).toContain(MSG_SIN_DATOS_SIN_RED);
    online.set(true); f.detectChanges();
    expect((f.nativeElement as HTMLElement).textContent).not.toContain('Esta pantalla necesita Internet');
  });

  it('«Cargando…» sin conexión se explica y con red muestra Cargando', () => {
    const f = TestBed.createComponent(CargandoComponent); f.detectChanges();
    expect((f.nativeElement as HTMLElement).textContent).toContain('Ábrala una vez con conexión');
    online.set(true); f.detectChanges();
    expect((f.nativeElement as HTMLElement).textContent).toContain('Cargando…');
  });
});

describe('Espejo del carrito (E1)', () => {
  const carrito = { sucursal_id: 1, sucursal: 'Centro', items: [{ id: 1, variante_id: 100, cantidad: 2 }], total_unidades: 2, subtotal: '200.00', descuento: '0.00', iva_incluido: '0.00', total: '200.00', puede_pagar: true, avisos: [] } as unknown as Carrito;
  const guardado = new Map<string, unknown>();

  it('cada carrito que llega del servidor se copia aparte y se puede leer sin red, sin mezclarse con el carrito local pendiente', async () => {
    guardado.clear();
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({ providers: [
      { provide: ComprasApi, useValue: { carrito: () => ({ subscribe: ({ next }: { next: (c: Carrito) => void }) => next(carrito) }) } },
      { provide: AuthService, useValue: { rol: () => 'Administrador', sesion: () => ({ empresa: { id: 1 }, usuario: { id: 5 } }) } },
      { provide: LocalDbService, useValue: { guardarCarritoLocal: async (k: string, v: unknown) => { guardado.set(k, v); }, leerCarritoLocal: async (k: string) => guardado.get(k) } },
      { provide: CatalogoLocalService, useValue: {} }, { provide: ColaOperacionesService, useValue: {} }, { provide: ToastService, useValue: {} },
      { provide: ConnectivityService, useValue: { online: signal(false) } },
    ] });
    const estado = TestBed.inject(CarritoEstadoService);
    await estado.refrescar();
    expect(guardado.has('espejo:1:5')).toBe(true);
    expect((await estado.leerEspejo())?.total).toBe('200.00');
    expect(estado.carritoLocal()).toBeNull();  // lo pendiente de fusionar sigue vacío: no se duplican prendas al volver la red
  });
});
