import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../core/auth/auth.service';
import { ROL } from '../core/models';
import { ConnectivityService } from '../core/offline/connectivity.service';
import { CarritoEstadoService } from '../core/carrito/carrito-estado.service';
import { ReservaBorradorService } from '../core/reservas/reserva-borrador.service';
import { ConfirmarSalidaComponent } from '../core/ui/confirmar-salida.component';
import { NotificacionesComponent } from '../core/ui/notificaciones.component';

interface Item { ruta: string; texto: string; icono: string; operativo?: boolean; }

const NAV_PLATAFORMA: Item[] = [
  { ruta: '/plataforma/empresas', texto: 'Empresas', icono: '🏢' },
  { ruta: '/plataforma/planes', texto: 'Planes', icono: '🏷️' },
];
const NAV_EMPRESA: Item[] = [
  { ruta: '/empresa/plan', texto: 'Mi plan', icono: '📋' },
  { ruta: '/empresa/usuarios', texto: 'Usuarios y roles', icono: '👥', operativo: true },
  { ruta: '/empresa/sucursales', texto: 'Sucursales', icono: '🏬', operativo: true },
  { ruta: '/empresa/catalogo/productos', texto: 'Productos', icono: '👗', operativo: true },
  { ruta: '/empresa/catalogo/atributos', texto: 'Categorías, tallas y colores', icono: '🎨', operativo: true },
  { ruta: '/empresa/catalogo/temporadas', texto: 'Temporadas y colecciones', icono: '🗓️', operativo: true },
  { ruta: '/empresa/catalogo/promociones', texto: 'Promociones', icono: '🏷️', operativo: true },
  { ruta: '/empresa/proveedores', texto: 'Proveedores', icono: '🚚', operativo: true },
  { ruta: '/empresa/abastecimiento', texto: 'Abastecimiento', icono: '📦', operativo: true },
  { ruta: '/empresa/inventario/global', texto: 'Inventario global', icono: '📊', operativo: true },
];
const NAV_CAJERO: Item[] = [
  { ruta: '/pos/caja', texto: 'Caja', icono: '🧾' },
];
const NAV_ENCARGADO: Item[] = [
  { ruta: '/sucursal/caja', texto: 'Caja', icono: '🧾' },
  { ruta: '/sucursal/ventas', texto: 'Ventas de la sucursal', icono: '📈' },
  { ruta: '/sucursal/reservas', texto: 'Reservas', icono: '📅' },
  { ruta: '/sucursal/atencion', texto: 'Atención en mostrador', icono: '🛎️' },
  { ruta: '/sucursal/inventario', texto: 'Inventario', icono: '📊' },
  { ruta: '/sucursal/recepciones', texto: 'Recepción de mercadería', icono: '📥' },
  { ruta: '/sucursal/movimientos', texto: 'Movimientos', icono: '🧾' },
];
const NAV_PROVEEDOR: Item[] = [
  { ruta: '/proveedor', texto: 'Mis envíos y propuestas', icono: '🚚' },
];
const NAV_CLIENTE: Item[] = [
  { ruta: '/tienda/catalogo', texto: 'Catálogo', icono: '🛍️' },
  { ruta: '/tienda/carrito', texto: 'Mi carrito', icono: '🛒' },
  { ruta: '/tienda/compras', texto: 'Mis compras', icono: '🧾' },
  { ruta: '/tienda/reservar', texto: 'Mi reserva', icono: '🧺' },
  { ruta: '/tienda/reservas', texto: 'Mis reservas', icono: '📅' },
];

const porRol: Record<string, Item[]> = {
  [ROL.SUPER]: NAV_PLATAFORMA, [ROL.CLIENTE]: NAV_CLIENTE, [ROL.ENCARGADO]: NAV_ENCARGADO, [ROL.CAJERO]: NAV_CAJERO, [ROL.PROVEEDOR]: NAV_PROVEEDOR,
};

/** Estructura común de los paneles: menú por rol, datos de la empresa y aviso de conectividad. */
@Component({
  selector: 'app-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, ConfirmarSalidaComponent, NotificacionesComponent],
  template: `
    <div class="layout">
      <aside class="side">
        <div class="brand"><span class="logo">F</span><div><strong>FashionStore</strong><small>SaaS</small></div></div>
        <nav aria-label="Principal">
          @for (it of items(); track it.ruta) {
            @if (it.operativo && auth.restringido()) {
              <span class="link disabled" title="Suscripción no vigente"><i>{{ it.icono }}</i>{{ it.texto }}<em>🔒</em></span>
            } @else {
              <a class="link" [routerLink]="it.ruta" routerLinkActive="activo"><i>{{ it.icono }}</i>{{ it.texto }}@if (it.ruta === '/tienda/reservar' && borrador.total() > 0) { <em class="cuenta">{{ borrador.total() }}</em> }@if (it.ruta === '/tienda/carrito' && carrito.total() > 0) { <em class="cuenta">{{ carrito.total() }}</em> }</a>
            }
          }
        </nav>
        <div class="user">
          <div class="who">
            <strong>{{ s()?.usuario?.nombre }} {{ s()?.usuario?.apellidos }}</strong>
            <small>{{ s()?.usuario?.rol }}{{ s()?.empresa ? ' · ' + s()?.empresa?.codigo : '' }}</small>
          </div>
          <button class="btn sm ghost out" (click)="confirmarSalida.set(true)">Cerrar sesión</button>
        </div>
      </aside>
      <div class="main">
        @if (!net.online()) {
          <div class="offline" role="status">Sin conexión. Se muestra la información almacenada, que puede estar desactualizada.</div>
        }
        @if (s()?.empresa) {
          <div class="topbar">
            <span><strong>{{ s()?.empresa?.razon_social }}</strong></span>
            <span class="row"><app-notificaciones />
            @if (s()?.suscripcion; as sus) {
             @if (auth.rol() !== 'Cliente') {
              <span class="badge" [class.ok]="sus.estado === 'ACTIVA'" [class.danger]="sus.estado !== 'ACTIVA'">
                Plan {{ sus.plan.nombre }} · {{ sus.estado }}
              </span>
             }
            }</span>
          </div>
        }
        <router-outlet />
      </div>
      @if (confirmarSalida()) { <app-confirmar-salida (cancelar)="confirmarSalida.set(false)" (confirmar)="salir()" /> }
    </div>`,
  styles: `
    .layout { display: grid; grid-template-columns: 250px 1fr; min-height: 100vh; }
    .side { background: var(--side); color: var(--side-ink); padding: 1.25rem .9rem; display: flex; flex-direction: column; gap: 1.5rem; position: sticky; top: 0; height: 100vh; }
    .brand { display: flex; gap: .7rem; align-items: center; padding: 0 .4rem; }
    .brand strong { font-family: var(--serif); font-size: 1.1rem; display: block; line-height: 1.1; } .brand small { color: #a79fb2; letter-spacing: .15em; font-size: .7rem; }
    .logo { width: 36px; height: 36px; border-radius: 10px; background: var(--accent); display: grid; place-items: center; font-family: var(--serif); font-size: 1.3rem; color: #fff; }
    nav { display: grid; gap: .2rem; }
    .link { display: flex; align-items: center; gap: .65rem; padding: .6rem .7rem; border-radius: 9px; color: var(--side-ink); text-decoration: none; font-weight: 500; }
    .link:hover { background: rgba(255,255,255,.07); text-decoration: none; } .link.activo { background: rgba(255,255,255,.13); }
    .link i { font-style: normal; width: 1.3rem; text-align: center; } .link em { margin-left: auto; font-style: normal; }
    .link.disabled { opacity: .45; cursor: not-allowed; }
    .cuenta { margin-left: auto; background: var(--accent); color: #fff; border-radius: 999px; font-size: .72rem; padding: 0 .45rem; font-weight: 700; }
    .user { margin-top: auto; display: grid; gap: .5rem; padding: .8rem; border-top: 1px solid rgba(255,255,255,.12); }
    .who strong { display: block; font-size: .9rem; } .who small { color: #a79fb2; }
    .out { color: var(--side-ink); justify-self: start; border: 1px solid rgba(255,255,255,.2); }
    .out:hover:not(:disabled) { background: rgba(255,255,255,.1) !important; border-color: rgba(255,255,255,.3) !important; }
    .main { min-width: 0; }
    .topbar { display: flex; justify-content: space-between; align-items: center; gap: 1rem; padding: .7rem 1.5rem; background: var(--surface); border-bottom: 1px solid var(--line); flex-wrap: wrap; }
    .offline { background: #fbefd9; color: #6b4000; padding: .55rem 1.5rem; font-size: .88rem; border-bottom: 1px solid #efd5a5; }
    @media (max-width: 820px) {
      .layout { grid-template-columns: 1fr; }
      .side { position: static; height: auto; flex-direction: row; flex-wrap: wrap; align-items: center; padding: .7rem; gap: .6rem; }
      nav { display: flex; flex-wrap: wrap; } .user { margin: 0 0 0 auto; border: 0; padding: 0; } .who { display: none; }
    }`,
})
export class ShellComponent {
  readonly auth = inject(AuthService);
  readonly net = inject(ConnectivityService);
  readonly borrador = inject(ReservaBorradorService);
  readonly carrito = inject(CarritoEstadoService);
  readonly s = this.auth.sesion;
  readonly confirmarSalida = signal(false);
  salir() { this.confirmarSalida.set(false); this.auth.cerrarSesion(); }
  readonly items = computed<Item[]>(() => porRol[this.auth.rol() as string] ?? NAV_EMPRESA);
}
