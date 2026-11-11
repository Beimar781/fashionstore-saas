import { DatePipe } from '@angular/common';
import { Component, OnInit, effect, inject, signal } from '@angular/core';
import { ColaOperacionesService } from '../../core/offline/cola-operaciones.service';
import { ConnectivityService } from '../../core/offline/connectivity.service';
import { IntentoSync, LocalDbService } from '../../core/offline/local-db.service';

/** Pantalla de demostración para la defensa: el interruptor «Simular sin conexión», la cola en vivo y el registro de sincronización en una sola vista. */
@Component({
  selector: 'app-demostracion',
  imports: [DatePipe],
  template: `
    <section class="card pad stack">
      <div class="row between">
        <div><h2>Demostración</h2><p class="small muted">Active «Simular sin conexión», registre operaciones en las pantallas normales y mire cómo se acumulan; al apagarlo se sincronizan solas.</p></div>
        <label class="check"><input type="checkbox" [checked]="red.simulado()" (change)="red.simular($any($event.target).checked)" /> <strong>Simular sin conexión</strong></label>
      </div>
      <div class="row" style="flex-wrap:wrap">
        <span class="badge" [class.ok]="red.online() && !cola.sincronizando()" [class.warn]="!red.online() || cola.sincronizando()">{{ cola.sincronizando() ? 'Sincronizando…' : red.online() ? 'En línea' : 'Sin conexión' }}</span>
        @for (e of conteo(); track e.texto) { <span class="badge" [class.warn]="e.clase === 'warn'" [class.ok]="e.clase === 'ok'" [class.danger]="e.clase === 'danger'">{{ e.texto }}: {{ e.n }}</span> }
        <button class="btn sm primary" (click)="cola.sincronizar()" [disabled]="cola.sincronizando() || !red.online() || !cola.pendientes().length">Sincronizar ahora</button>
      </div>
      <div class="demo-grid">
        <div>
          <h3>Cola en vivo</h3>
          @for (o of cola.operaciones().slice(0, 8); track o.id) {
            <div class="small fila"><span class="badge" [class.ok]="o.estado === 'CONFIRMADA'" [class.danger]="o.estado === 'RECHAZADA'" [class.warn]="o.estado === 'EN_CONFLICTO' || o.estado === 'ENVIADA'">{{ etiqueta(o.estado) }}</span> {{ o.resumen }} <span class="muted">{{ o.creada_en | date: 'HH:mm:ss' }}</span></div>
          } @empty { <p class="muted small">La cola está vacía.</p> }
        </div>
        <div>
          <h3>Registro de sincronización</h3>
          @for (f of registro(); track f.id) { <div class="small fila"><strong>{{ f.tipo }}</strong> · {{ f.resultado }} <span class="muted">{{ f.fecha | date: 'HH:mm:ss' }}</span></div> }
          @empty { <p class="muted small">Todavía no se intentó sincronizar nada.</p> }
        </div>
      </div>
    </section>`,
  styles: `.demo-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.2rem; } .fila { padding: .25rem 0; border-bottom: 1px solid var(--line); } @media (max-width: 800px) { .demo-grid { grid-template-columns: 1fr; } }`,
})
export class DemostracionComponent implements OnInit {
  readonly cola = inject(ColaOperacionesService);
  readonly red = inject(ConnectivityService);
  private db = inject(LocalDbService);

  readonly registro = signal<IntentoSync[]>([]);

  constructor() {
    effect(() => { this.cola.refresco(); this.cola.operaciones(); void this.cargarRegistro(); });  // se actualiza sola con cada cambio de la cola
  }

  ngOnInit() { void this.cola.cargar(); }

  private async cargarRegistro() { this.registro.set(await this.db.registroSincronizacion(8)); }

  etiqueta(e: string) { return ({ REGISTRADA_LOCAL: 'Pendiente', ENVIADA: 'Enviada', CONFIRMADA: 'Confirmada', RECHAZADA: 'Rechazada', EN_CONFLICTO: 'En conflicto' } as Record<string, string>)[e] ?? e; }

  conteo() {
    const n = (...estados: string[]) => this.cola.operaciones().filter((o) => estados.includes(o.estado)).length;
    return [{ texto: 'Pendientes', n: n('REGISTRADA_LOCAL', 'ENVIADA'), clase: 'warn' }, { texto: 'Confirmadas', n: n('CONFIRMADA'), clase: 'ok' }, { texto: 'En conflicto', n: n('EN_CONFLICTO'), clase: 'warn' }, { texto: 'Rechazadas', n: n('RECHAZADA'), clase: 'danger' }];
  }
}
