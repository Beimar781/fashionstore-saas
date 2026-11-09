import { DatePipe } from '@angular/common';
import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { ReservasApi } from '../api/reservas.api';
import { AuthService } from '../auth/auth.service';
import { ROL } from '../models';
import { PushService } from '../push/push.service';
import { Notificacion } from '../reservas.models';
import { LocalDbService } from '../offline/local-db.service';
import { ConnectivityService } from '../offline/connectivity.service';

/** RF11 · Campana de avisos de la barra superior: reservas nuevas para la sucursal, estado de las reservas para el cliente. */
@Component({
  selector: 'app-notificaciones',
  imports: [DatePipe],
  template: `
    <div class="campana">
      <button type="button" class="btn sm ghost" (click)="alternar()" [attr.aria-label]="'Notificaciones: ' + sinLeer() + ' sin leer'" aria-haspopup="true" [attr.aria-expanded]="abierto()">
        🔔 @if (sinLeer() > 0) { <span class="contador">{{ sinLeer() }}</span> }
      </button>
      @if (abierto()) {
        <div class="panel card" role="dialog" aria-label="Notificaciones">
          <div class="row between cabecera"><strong>Notificaciones</strong>
            @if (sinLeer() > 0) { <button type="button" class="btn sm ghost" (click)="leerTodas()">Marcar todas como leídas</button> }</div>
          <div class="push row between">
            <span class="small muted">{{ push.activo() ? (push.simulado() ? 'Avisos en este dispositivo: simulados' : 'Avisos activados en este dispositivo') : 'Reciba avisos importantes aunque no tenga la tienda abierta.' }}</span>
            @if (push.activo()) { <button type="button" class="btn sm ghost" (click)="apagarPush()">Desactivar</button> }
            @else { <button type="button" class="btn sm" (click)="encenderPush()">Activar avisos</button> }
          </div>
          @if (mensajePush()) { <div class="small muted push">{{ mensajePush() }}</div> }
          @if (!avisos().length) { <div class="empty">Sin notificaciones.</div> }
          @for (n of avisos(); track n.id) {
            <button type="button" class="aviso" [class.nueva]="!n.leida" (click)="leer(n)">
              <strong>{{ n.titulo }}</strong><span>{{ n.mensaje }}</span><small class="muted">{{ n.creada_en | date: 'dd/MM HH:mm' }}</small>
            </button>
          }
        </div>
      }
    </div>`,
  styles: `
    .campana { position: relative; }
    .contador { background: var(--danger); color: #fff; border-radius: 999px; font-size: .7rem; padding: 0 .4rem; margin-left: .15rem; font-weight: 700; }
    .panel { position: absolute; right: 0; top: calc(100% + .4rem); width: min(380px, 92vw); max-height: 70vh; overflow: auto; z-index: 40; padding: .3rem; }
    .push { padding: .5rem .6rem; border-bottom: 1px solid var(--line); gap: .6rem; }
    .cabecera { padding: .5rem .6rem; border-bottom: 1px solid var(--line); }
    .aviso { display: grid; gap: .15rem; text-align: left; width: 100%; border: 0; background: transparent; font: inherit; color: inherit; padding: .6rem; border-bottom: 1px solid var(--line); cursor: pointer; border-radius: 8px; }
    .aviso:hover { background: #faf8f5; } .aviso span { font-size: .88rem; } .aviso.nueva { background: var(--accent-soft); }`,
})
export class NotificacionesComponent implements OnInit, OnDestroy {
  private api = inject(ReservasApi);
  private auth = inject(AuthService);
  private db = inject(LocalDbService);
  private red = inject(ConnectivityService);
  readonly push = inject(PushService);
  readonly mensajePush = signal('');
  readonly sinLeer = signal(0);
  readonly avisos = signal<Notificacion[]>([]);
  readonly abierto = signal(false);
  private reloj?: ReturnType<typeof setInterval>;
  private alVolverRed = () => { void this.sincronizarLecturas(); this.contar(); if (this.abierto()) this.cargar(); };

  ngOnInit() {
    void this.push.reanudar(this.auth.rol() === ROL.CLIENTE);  // si ya los había activado se registran para esta cuenta; al Cliente se le pide el permiso la primera vez
    this.contar();
    window.addEventListener('online', this.alVolverRed);
    this.reloj = setInterval(() => { this.contar(); if (this.abierto()) this.cargar(); }, 30000);  // sin websockets: se consulta cada 30 s
  }
  ngOnDestroy() { clearInterval(this.reloj); window.removeEventListener('online', this.alVolverRed); }

  alternar() { this.abierto.update((a) => !a); if (this.abierto()) this.cargar(); }

  async encenderPush() {
    const r = await this.push.activar();
    this.mensajePush.set(r === 'denegado' ? 'El navegador bloqueó los avisos: permítalos en la configuración del sitio.' : r === 'error' ? 'No se pudieron activar los avisos. Intente de nuevo.' : '');
  }
  async apagarPush() { await this.push.desactivar(); this.mensajePush.set(''); }

  private clave() { const s = this.auth.sesion(); return `${s?.empresa?.id ?? 0}:${s?.usuario.id ?? 0}`; }
  private contar() { if (!this.red.online()) { this.sinLeer.set(this.avisos().filter((n) => !n.leida).length); return; } this.api.sinLeer().subscribe({ next: (r) => this.sinLeer.set(r.no_leidas), error: () => {} }); }
  private async cargar() {
    const cache = await this.db.leerAvisosLocal<Notificacion[]>(this.clave());
    if (!this.red.online()) { if (cache) this.avisos.set(cache); this.contar(); return; }
    this.api.notificaciones().subscribe({ next: (r) => { this.avisos.set(r); void this.db.guardarAvisosLocal(this.clave(), r); }, error: () => { if (cache) this.avisos.set(cache); } });
  }

  private async sincronizarLecturas() {
    if (!this.red.online()) return;
    const clave = this.clave();
    const pendientes = await this.db.leerLecturasPendientes(clave);
    const fallidas: number[] = [];
    for (const id of pendientes) await new Promise<void>((resolver) => this.api.leer(id).subscribe({ next: () => resolver(), error: () => { fallidas.push(id); resolver(); } }));
    await this.db.guardarLecturasPendientes(clave, fallidas);
  }

  leer(n: Notificacion) {
    if (n.leida) return;
    const clave = this.clave();
    this.avisos.update((l) => l.map((x) => (x.id === n.id ? { ...x, leida: true } : x)));
    void this.db.guardarAvisosLocal(clave, this.avisos());
    if (!this.red.online()) { void this.db.leerLecturasPendientes(clave).then((ids) => this.db.guardarLecturasPendientes(clave, [...ids, n.id])); this.contar(); return; }
    this.api.leer(n.id).subscribe({ next: () => this.contar(), error: () => { void this.db.leerLecturasPendientes(clave).then((ids) => this.db.guardarLecturasPendientes(clave, [...ids, n.id])); } });
  }
  leerTodas() {
    const ids = this.avisos().filter((x) => !x.leida).map((x) => x.id);
    this.avisos.update((l) => l.map((x) => ({ ...x, leida: true })));
    this.sinLeer.set(0);
    void this.db.guardarAvisosLocal(this.clave(), this.avisos());
    if (!this.red.online()) { void this.db.leerLecturasPendientes(this.clave()).then((previas) => this.db.guardarLecturasPendientes(this.clave(), [...previas, ...ids])); return; }
    this.api.leerTodas().subscribe({ next: (r) => this.sinLeer.set(r.no_leidas), error: () => void this.db.guardarLecturasPendientes(this.clave(), ids) });
  }
}
