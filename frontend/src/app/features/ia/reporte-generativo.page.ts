import { DatePipe, JsonPipe } from '@angular/common';
import { ErrorComponent } from '../../core/ui/vacio.component';
import { ColaOperacionesService } from '../../core/offline/cola-operaciones.service';
import { NecesitaInternetDirective } from '../../core/ui/necesita-internet.directive';
import { Component, NgZone, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ReportesApi } from '../../core/api/reportes.api';
import { ReporteGenerativo } from '../../core/reportes.models';
import { BsPipe } from '../../core/formato-bs';
import { ConnectivityService } from '../../core/offline/connectivity.service';
import { ToastService, mensajeError } from '../../core/ui/toast.service';
import { VozService } from '../../core/voz/voz.service';

const EJEMPLOS = ['Ventas de este mes', 'El producto más vendido de la semana', 'Reservas de la sucursal centro', 'Pagos rechazados de este mes', 'Estado del inventario y stock bajo'];

/** CU-23 · Reportes generativos: el Administrador escribe o dicta (Web Speech API del navegador) lo que necesita y el sistema interpreta la petición y genera el reporte. */
@Component({
  selector: 'app-reporte-generativo',
  imports: [ErrorComponent, NecesitaInternetDirective, FormsModule, DatePipe, JsonPipe, BsPipe],
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
            @if (hayVoz) { <button type="button" class="btn" [class.grabando]="escuchando() && !conversando()" necesitaInternet="El dictado por voz necesita Internet." (click)="dictar()" [disabled]="conversando()" [attr.aria-pressed]="escuchando()">{{ escuchando() && !conversando() ? '⏹ Detener' : '🎤 Dictar' }}</button>
              <button type="button" class="btn" [class.grabando]="conversando()" necesitaInternet="El chat de voz necesita Internet." (click)="conversando() ? terminarConversacion() : iniciarConversacion()" [attr.aria-pressed]="conversando()">{{ conversando() ? '⏹ Terminar conversación' : '🗣 Conversar' }}</button> }
            <button class="btn primary" necesitaInternet="Generar un reporte con IA necesita Internet." [disabled]="generando() || !prompt.trim()">{{ generando() ? 'Generando…' : 'Generar reporte' }}</button>
          </span>
        </div>
        @if (!hayVoz) { <p class="muted small">Este navegador no permite dictar por voz; escriba su petición.</p> }
        @if (conversando()) { <p class="small" role="status">🗣 Conversación activa: {{ voz.hablando() ? 'leyendo el reporte…' : generando() ? 'generando el reporte…' : escuchando() ? 'escuchando, diga su petición.' : 'preparando el micrófono…' }} Diga «terminar» para salir o «repite» para volver a escucharlo.</p> }
        @else if (escuchando()) { <p class="small" role="status">🎙 Escuchando… hable ahora.</p> }
        @if (error()) { <app-error [texto]="error()" /> }
      </form>

      <div class="layout">
        <section class="stack">
          @if (actual(); as r) {
            <div class="card pad stack">
              <div class="row between"><h2>Reporte generado</h2><span class="badge" [class.ok]="r.origen === 'IA'" [class.warn]="r.origen === 'REGLAS'">{{ r.origen === 'IA' ? 'Interpretado por IA' : 'Reglas de respaldo' }}</span></div>
              <pre class="reporte">{{ r.texto }}</pre>
              @for (g of porSucursal(r); track g.sucursal) {
                <h3>{{ g.sucursal }}</h3>
                <div class="table-wrap"><table>
                  <thead><tr><th>#</th><th>Producto</th><th class="right">Unidades</th><th class="right">Ingresos</th></tr></thead>
                  <tbody>
                    @for (f of g.ranking; track f.producto; let i = $index) { <tr><td>{{ i + 1 }}</td><td>{{ f.producto }}</td><td class="right">{{ f.unidades }}</td><td class="right">{{ f.ingresos | bs }}</td></tr> }
                    @empty { <tr><td colspan="4" class="empty">Sin ventas de productos en el periodo.</td></tr> }
                  </tbody>
                </table></div>
              }
              <details><summary class="small">Cómo se interpretó la petición</summary><pre class="small">{{ r.especificacion | json }}</pre></details>
              <div class="row">@if (voz.disponible) { <button class="btn" [class.grabando]="voz.hablando()" (click)="voz.hablando() ? voz.detener() : voz.hablar(r.texto)">{{ voz.hablando() ? '⏹ Detener lectura' : '🔊 Escuchar' }}</button> }<button class="btn" (click)="copiar(r)">Copiar texto</button><button class="btn" (click)="imprimir()">Imprimir</button><button class="btn" necesitaInternet="Descargar el Excel necesita Internet." (click)="descargar(r, 'xlsx')">⬇ Descargar Excel</button><button class="btn" necesitaInternet="Descargar el PDF necesita Internet." (click)="descargar(r, 'pdf')">⬇ Descargar PDF</button></div>
            </div>
          } @else { <div class="card empty">El reporte aparecerá aquí.</div> }
        </section>
        <aside class="card pad stack"><h3>Reportes anteriores</h3>
          @for (h of historial(); track h.id) {
            <button type="button" class="hist" (click)="actual.set(h)"><strong class="small">{{ h.prompt }}</strong><span class="small muted">{{ h.creado_en | date: 'dd/MM HH:mm' }} · {{ h.origen === 'IA' ? 'IA' : 'Reglas' }}</span></button>
            <span class="row small"><button type="button" class="btn sm ghost" necesitaInternet="Descargar el Excel necesita Internet." (click)="descargar(h, 'xlsx')">Excel</button><button type="button" class="btn sm ghost" necesitaInternet="Descargar el PDF necesita Internet." (click)="descargar(h, 'pdf')">PDF</button></span>
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
  private red = inject(ConnectivityService);
  readonly voz = inject(VozService);
  readonly conversando = signal(false);
  private silencios = 0;

  readonly ejemplos = EJEMPLOS;
  readonly actual = signal<ReporteGenerativo | null>(null);
  readonly historial = signal<ReporteGenerativo[]>([]);
  readonly generando = signal(false);
  readonly escuchando = signal(false);
  readonly error = signal('');
  prompt = '';
  private reconocimiento: any = null;
  readonly hayVoz = !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);

  private readonly recargaAlVolverLaRed = inject(ColaOperacionesService).alRefrescar(() => this.ngOnInit());  // al volver la red se vuelve a leer el historial
  ngOnInit() { this.api.historialReportes().subscribe({ next: (h) => { this.historial.set(h); this.actual.set(h[0] ?? null); }, error: (e) => this.error.set(mensajeError(e)) }); }
  ngOnDestroy() { this.conversando.set(false); this.reconocimiento?.stop?.(); this.voz.detener(); }

  /** Genera el reporte con lo escrito o dictado; devuelve el reporte o null si falló (el mensaje queda en pantalla). */
  generar(): Promise<ReporteGenerativo | null> {
    if (!this.red.online()) { this.error.set('Generar un reporte con IA necesita Internet.'); return Promise.resolve(null); }
    this.error.set(''); this.generando.set(true);
    return new Promise((resolver) => this.api.generarReporte(this.prompt).subscribe({
      next: (r) => { this.generando.set(false); this.actual.set(r); this.historial.update((h) => [r, ...h]); resolver(r); },
      error: (e) => { this.generando.set(false); this.error.set(mensajeError(e)); resolver(null); },
    }));
  }

  /** Chat de voz: escucha la petición, genera el reporte, lo lee en voz alta y vuelve a escuchar, hasta que se diga «terminar». */
  iniciarConversacion() {
    this.silencios = 0; this.conversando.set(true); this.error.set('');
    void this.voz.hablar('Hola. Dígame qué reporte necesita.').then(() => this.escucharPeticion());
  }

  terminarConversacion() { this.conversando.set(false); this.reconocimiento?.stop?.(); this.voz.detener(); this.escuchando.set(false); }

  private escucharPeticion() {
    if (!this.conversando()) return;
    const Reconocimiento = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const rec = (this.reconocimiento = new Reconocimiento());
    rec.lang = 'es-BO'; rec.interimResults = true;
    let dicho = '';
    rec.onresult = (ev: any) => this.zona.run(() => { dicho = Array.from(ev.results as ArrayLike<any>).map((r) => r[0].transcript).join(' ').trim(); this.prompt = dicho; });
    rec.onerror = (ev: any) => this.zona.run(() => {
      if (ev.error === 'no-speech' || ev.error === 'aborted') return;  // silencio: lo maneja onend
      this.terminarConversacion();
      this.toast.error(ev.error === 'not-allowed' ? 'Permita el uso del micrófono para conversar.' : 'No se pudo captar la voz. Intente nuevamente.');
    });
    rec.onend = () => this.zona.run(() => { this.escuchando.set(false); if (this.conversando()) void this.alTerminarDeEscuchar(dicho); });
    rec.start(); this.escuchando.set(true);
  }

  private async alTerminarDeEscuchar(dicho: string) {
    const orden = dicho.toLowerCase().replace(/[.,¡!¿?]/g, '').trim();
    if (!orden) {  // tres silencios seguidos cierran la conversación
      if (++this.silencios >= 3) { await this.voz.hablar('No escuché nada. Termino la conversación.'); this.terminarConversacion(); return; }
      this.escucharPeticion(); return;
    }
    this.silencios = 0;
    if (/^(terminar|terminemos|salir|adiós|adios|fin|detener|cerrar)\b/.test(orden)) { await this.voz.hablar('Conversación terminada.'); this.terminarConversacion(); return; }
    if (/^(repite|repetir|otra vez)\b/.test(orden) && this.actual()) { await this.voz.hablar(this.actual()!.texto); this.escucharPeticion(); return; }
    const reporte = await this.generar();
    await this.voz.hablar(reporte ? reporte.texto : this.error() || 'No pude generar el reporte.');
    this.escucharPeticion();
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

  /** CU-23: cuando se pide «por sucursal», el ranking llega en cifras.ranking_por_sucursal y se muestra una tabla por sucursal. */
  porSucursal(r: ReporteGenerativo): { sucursal: string; ranking: { producto: string; unidades: number; ingresos: string }[] }[] {
    return (r.datos['ranking_por_sucursal'] as ReturnType<ReporteGenerativoPage['porSucursal']> | undefined) ?? [];
  }

  copiar(r: ReporteGenerativo) { navigator.clipboard?.writeText(r.texto).then(() => this.toast.ok('Reporte copiado.')); }
  imprimir() { window.print(); }

  /** Excel o PDF con formato de reporte convencional, armado por el servidor según el reporte interpretado. */
  descargar(r: ReporteGenerativo, formato: 'xlsx' | 'pdf') {
    this.api.exportarReporteIa(r.id, formato).subscribe({
      next: (blob) => { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `reporte-${r.id}.${formato}`; a.click(); URL.revokeObjectURL(a.href); },
      error: (e) => this.error.set(mensajeError(e)),
    });
  }
}
