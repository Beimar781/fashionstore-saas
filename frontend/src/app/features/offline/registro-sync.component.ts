import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { IntentoSync, LocalDbService } from '../../core/offline/local-db.service';
import { ToastService } from '../../core/ui/toast.service';

/** RNF10 · Registro de sincronización: cada intento de enviar una operación con su resultado, código y motivo técnico (sin datos personales). */
@Component({
  selector: 'app-registro-sync',
  imports: [DatePipe],
  template: `
    <div class="card pad stack">
      <div class="row between"><h3>Registro de sincronización</h3><span class="row"><button class="btn sm" (click)="cargar()">Actualizar</button><button class="btn sm primary" (click)="copiar()">Copiar diagnóstico</button></span></div>
      @for (f of filas(); track f.id) {
        <div class="small"><strong>{{ f.tipo }}</strong> · intento {{ f.intento }} · {{ f.resultado }} ({{ f.codigo }}) <span class="muted">{{ f.fecha | date: 'dd/MM HH:mm:ss' }}</span>@if (f.motivo) { <br />{{ f.motivo }} }<br /><span class="muted">{{ f.operacion_id }}</span></div>
      } @empty { <p class="muted small">Todavía no se intentó sincronizar nada.</p> }
    </div>`,
})
export class RegistroSyncComponent implements OnInit {
  private db = inject(LocalDbService);
  private toast = inject(ToastService);
  readonly filas = signal<IntentoSync[]>([]);

  ngOnInit() { void this.cargar(); }
  async cargar() { this.filas.set(await this.db.registroSincronizacion()); }

  /** Texto para pegar en un mensaje a soporte: solo datos técnicos. */
  async copiar() {
    const texto = ['Diagnóstico de sincronización de FashionStore', ...this.filas().map((f) => `${f.fecha} · ${f.tipo} ${f.operacion_id} · intento ${f.intento} · ${f.resultado} (${f.codigo})${f.motivo ? ' · ' + f.motivo : ''}`)].join('\n');
    try { await navigator.clipboard.writeText(texto); this.toast.ok('Diagnóstico copiado.'); } catch { this.toast.error('No se pudo copiar. Seleccione el texto y cópielo a mano.'); }
  }
}
