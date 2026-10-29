import { DatePipe, JsonPipe } from '@angular/common';
import { Component, NgZone, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ReportesApi } from '../../core/api/reportes.api';
import { ReporteGenerativo } from '../../core/reportes.models';
import { ToastService, mensajeError } from '../../core/ui/toast.service';

const EJEMPLOS = ['Ventas de este mes', 'El producto más vendido de la semana', 'Reservas de la sucursal centro', 'Pagos rechazados de este mes', 'Estado del inventario y stock bajo'];

/** CU-23 · Reportes generativos: el Administrador escribe o dicta (Web Speech API del navegador) lo que necesita y el sistema interpreta la petición y genera el reporte. */
@Component({
  selector: 'app-reporte-generativo',
  imports: [FormsModule, DatePipe, JsonPipe],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Reportes con IA</h1><p>Escriba o dicte lo que necesita, por ejemplo «ventas del último mes» o «el producto menos vendido de la sucursal centro».</p></div></div>

      <form class="card pad stack" (ngSubmit)="generar()">
        <label>Su petición
          <textarea name="p" rows="3" [(ngModel)]="prompt" maxlength="500" placeholder="Escriba aquí o presione el micrófono para dictar" [disabled]="generando()"></textarea></label>
        <div class="row between">
          <span class="row" style="flex-wrap:wrap">
            @for (e of ejemplos; track e) { <button type="button" class="chip" (click)="prompt = e">{{ e }}</button> }
          </span>
          <span class="row">
            @if (hayVoz) { <button type="button" class="btn" [class.grabando]="escuchando()" (click)="dictar()" [attr.aria-pressed]="escuchando()">{{ escuchando() ? '⏹ Detener' : '🎤 Dictar' }}</button> }
            <button class="btn primary" [disabled]="generando() || !prompt.trim()">{{ generando() ? 'Generando…' : 'Generar reporte' }}</button>
          </span>
        </div>
        @if (!hayVoz) { <p class="muted small">Este navegador no permite dictar por voz; escriba su petición.</p> }
        @if (escuchando()) { <p class="small" role="status">🎙 Escuchando… hable ahora.</p> }
        @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
      </form>

      <div class="layout">
        <section class="stack">
          @if (actual(); as r) {
            <div class="card pad stack">
              <div class="row between"><h2>Reporte generado</h2><span class="badge" [class.ok]="r.origen === 'IA'" [class.warn]="r.origen === 'REGLAS'">{{ r.origen === 'IA' ? 'Interpretado por IA' : 'Reglas de respaldo' }}</span></div>
              <pre class="reporte">{{ r.texto }}</pre>
              <details><summary class="small">Cómo se interpretó la petición</summary><pre class="small">{{ r.especificacion | json }}</pre></details>
              <div class="row"><button class="btn" (click)="copiar(r)">Copiar texto</button><button class="btn" (click)="imprimir()">Imprimir</button></div>
            </div>
          } @else { <div class="card empty">El reporte aparecerá aquí.</div> }
        </section>
        <aside class="card pad stack"><h3>Reportes anteriores</h3>
          @for (h of historial(); track h.id) {
            <button type="button" class="hist" (click)="actual.set(h)"><strong class="small">{{ h.prompt }}</strong><span class="small muted">{{ h.creado_en | date: 'dd/MM HH:mm' }} · {{ h.origen === 'IA' ? 'IA' : 'Reglas' }}</span></button>
          } @empty { <p class="muted small">Todavía no generó reportes.</p> }
        </aside>
      </div>
    </div>`,
  styles: `.layout { display: grid; grid-template-columns: 1fr 300px; gap: 1rem; margin-top: 1rem; } @media (max-width: 900px) { .layout { grid-template-columns: 1fr; } }
    .reporte { white-space: pre-wrap; font: .92rem/1.55 var(--sans, system-ui); margin: 0; background: var(--bg, #faf8f5); padding: 1rem; border-radius: 10px; }
    .chip { border: 1px solid var(--line); background: var(--surface); border-radius: 999px; padding: .25rem .7rem; font-size: .8rem; cursor: pointer; }
    .hist { display: grid; text-align: left; gap: .1rem; border: 1px solid var(--line); background: var(--surface); border-radius: 9px; padding: .5rem .7rem; cursor: pointer; }
    .grabando { background: #fde3e3; border-color: var(--danger); }`,
})
export class ReporteGenerativoPage implements OnInit, OnDestroy {
  private api = inject(ReportesApi);
  private toast = inject(ToastService);
  private zona = inject(NgZone);

  readonly ejemplos = EJEMPLOS;
  readonly actual = signal<ReporteGenerativo | null>(null);
  readonly historial = signal<ReporteGenerativo[]>([]);
  readonly generando = signal(false);
  readonly escuchando = signal(false);
  readonly error = signal('');
  prompt = '';
  private reconocimiento: any = null;
  readonly hayVoz = !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);

  ngOnInit() { this.api.historialReportes().subscribe({ next: (h) => { this.historial.set(h); this.actual.set(h[0] ?? null); }, error: (e) => this.error.set(mensajeError(e)) }); }
  ngOnDestroy() { this.reconocimiento?.stop?.(); }

  generar() {
    this.error.set(''); this.generando.set(true);
    this.api.generarReporte(this.prompt).subscribe({
      next: (r) => { this.generando.set(false); this.actual.set(r); this.historial.update((h) => [r, ...h]); },
      error: (e) => { this.generando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  /** Dictado por voz: la transcripción llena el cuadro; el reporte se genera cuando el administrador lo confirma. */
  dictar() {
    if (this.escuchando()) { this.reconocimiento?.stop(); return; }
    const Reconocimiento = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    this.reconocimiento = new Reconocimiento();
    this.reconocimiento.lang = 'es-BO';
    this.reconocimiento.interimResults = true;
    this.reconocimiento.onresult = (ev: any) => this.zona.run(() => { this.prompt = Array.from(ev.results as ArrayLike<any>).map((r) => r[0].transcript).join(' ').trim(); });
    this.reconocimiento.onerror = (ev: any) => this.zona.run(() => { this.escuchando.set(false); this.toast.error(ev.error === 'not-allowed' ? 'Permita el uso del micrófono para dictar.' : 'No se pudo captar la voz. Intente nuevamente.'); });
    this.reconocimiento.onend = () => this.zona.run(() => this.escuchando.set(false));
    this.reconocimiento.start();
    this.escuchando.set(true);
  }

  copiar(r: ReporteGenerativo) { navigator.clipboard?.writeText(r.texto).then(() => this.toast.ok('Reporte copiado.')); }
  imprimir() { window.print(); }
}
