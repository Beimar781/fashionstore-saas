import { DatePipe } from '@angular/common';
import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { ReservasApi } from '../api/reservas.api';
import { Notificacion } from '../reservas.models';

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
    .cabecera { padding: .5rem .6rem; border-bottom: 1px solid var(--line); }
    .aviso { display: grid; gap: .15rem; text-align: left; width: 100%; border: 0; background: transparent; font: inherit; color: inherit; padding: .6rem; border-bottom: 1px solid var(--line); cursor: pointer; border-radius: 8px; }
    .aviso:hover { background: #faf8f5; } .aviso span { font-size: .88rem; } .aviso.nueva { background: var(--accent-soft); }`,
})
export class NotificacionesComponent implements OnInit, OnDestroy {
  private api = inject(ReservasApi);
  readonly sinLeer = signal(0);
  readonly avisos = signal<Notificacion[]>([]);
  readonly abierto = signal(false);
  private reloj?: ReturnType<typeof setInterval>;

  ngOnInit() {
    this.contar();
    this.reloj = setInterval(() => { this.contar(); if (this.abierto()) this.cargar(); }, 30000);  // sin websockets: se consulta cada 30 s
  }
  ngOnDestroy() { clearInterval(this.reloj); }

  alternar() { this.abierto.update((a) => !a); if (this.abierto()) this.cargar(); }

  private contar() { this.api.sinLeer().subscribe({ next: (r) => this.sinLeer.set(r.no_leidas), error: () => {} }); }
  private cargar() { this.api.notificaciones().subscribe({ next: (r) => this.avisos.set(r), error: () => {} }); }

  leer(n: Notificacion) {
    if (n.leida) return;
    this.api.leer(n.id).subscribe(() => { this.avisos.update((l) => l.map((x) => (x.id === n.id ? { ...x, leida: true } : x))); this.contar(); });
  }
  leerTodas() { this.api.leerTodas().subscribe((r) => { this.sinLeer.set(r.no_leidas); this.avisos.update((l) => l.map((x) => ({ ...x, leida: true }))); }); }
}
