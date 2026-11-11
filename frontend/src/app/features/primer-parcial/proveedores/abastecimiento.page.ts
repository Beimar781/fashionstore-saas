import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { NecesitaInternetDirective } from '../../../core/ui/necesita-internet.directive';
import { VacioComponent, ErrorComponent } from '../../../core/ui/vacio.component';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../../core/auth/auth.service';
import { CatalogoAdminApi } from '../../../core/api/catalogo-admin.api';
import { ProveedoresApi } from '../../../core/api/proveedores.api';
import { Coleccion, GENEROS } from '../../../core/catalogo.models';
import { Lote, Propuesta, Proveedor, ResumenAbastecimiento, SucursalDestino, VarianteHabilitada } from '../../../core/inventario.models';
import { ROL } from '../../../core/models';
import { ColaOperacionesService } from '../../../core/offline/cola-operaciones.service';
import { ConnectivityService } from '../../../core/offline/connectivity.service';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';
import { BsPipe } from '../../../core/formato-bs';

type Pestana = 'avisos' | 'propuestas';
interface Linea { sku: string; producto: string; talla: string; color: string; cantidad: number; costo: number | null; }

/** CU-31 · Información de productos y abastecimiento. El Proveedor avisa remisiones y propone productos; el Administrador revisa. */
@Component({
  selector: 'app-abastecimiento',
  imports: [NecesitaInternetDirective, ErrorComponent, VacioComponent, BsPipe, FormsModule],
  template: `
    <div class="page">
      <div class="page-head">
        <div><h1>{{ esProveedor ? 'Mis envíos y propuestas' : 'Abastecimiento' }}</h1>
          <p>{{ esProveedor ? 'Avise la mercadería que despacha y proponga productos nuevos.' : 'Avisos de remisión de los proveedores y propuestas de producto por revisar.' }}</p></div>
        @if (pestana() === 'avisos') { <button necesitaInternet="Los avisos de remisión necesitan Internet (las propuestas sí se guardan sin conexión)." class="btn primary" (click)="abrirAviso()">+ Nuevo aviso de remisión</button> }
        @else if (esProveedor) { <button class="btn primary" (click)="abrirPropuesta()">+ Nueva propuesta</button> }
      </div>

      @if (!esProveedor && resumen(); as r) {
        <div class="grid cols-2" style="margin-bottom:1rem">
          <div class="card pad row between"><span>Lotes en tránsito por recibir</span><span class="badge" [class.warn]="r.lotes_en_transito > 0">{{ r.lotes_en_transito }}</span></div>
          <div class="card pad row between"><span>Propuestas por revisar</span><span class="badge" [class.warn]="r.propuestas_pendientes > 0">{{ r.propuestas_pendientes }}</span></div>
        </div>
      }

      <div class="tabs" role="tablist">
        <button role="tab" [class.activa]="pestana() === 'avisos'" (click)="pestana.set('avisos')">Avisos de remisión</button>
        <button role="tab" [class.activa]="pestana() === 'propuestas'" (click)="pestana.set('propuestas')">Propuestas de producto</button>
      </div>

      @if (pestana() === 'avisos') {
        <div class="card table-wrap">
          @if (!lotes().length) { <app-vacio>Aún no hay avisos de remisión.</app-vacio> } @else {
            <table>
              <thead><tr><th>Lote</th>@if (!esProveedor) { <th>Proveedor</th> }<th>Destino</th><th>Referencia</th><th class="right">Unidades</th><th>Estado</th><th></th></tr></thead>
              <tbody>
                @for (l of lotes(); track l.id) {
                  <tr>
                    <td><strong>{{ l.codigo }}</strong><div class="muted small">{{ l.creado_en.slice(0, 10) }}</div></td>
                    @if (!esProveedor) { <td>{{ l.proveedor }}</td> }
                    <td>{{ l.sucursal }}</td><td>{{ l.referencia || '—' }}</td><td class="right">{{ l.total_unidades }}</td>
                    <td><span class="badge" [class.warn]="l.estado === 'EN_TRANSITO'" [class.ok]="l.estado === 'RECIBIDO'" [class.danger]="l.estado === 'CANCELADO'">{{ textoEstado(l.estado) }}</span></td>
                    <td class="actions"><button class="btn sm" (click)="detalle.set(l)">Ver</button>
                      @if (l.estado === 'EN_TRANSITO') { <button necesitaInternet class="btn sm danger" (click)="cancelar(l)">Cancelar</button> }</td>
                  </tr>
                }
              </tbody>
            </table>
          }
        </div>
      } @else {
        <div class="card table-wrap">
          @if (!propuestas().length && !propuestasLocales().length) { <app-vacio>Aún no hay propuestas.</app-vacio> } @else {
            <table>
              <thead><tr><th>Producto propuesto</th>@if (!esProveedor) { <th>Proveedor</th> }<th>Colección</th><th class="right">Precio</th><th>Estado</th><th></th></tr></thead>
              <tbody>
                @for (l of propuestasLocales(); track l.op.id) {
                  <tr>
                    <td><strong>{{ l.nombre }}</strong><div class="muted small">{{ l.material }}</div></td>
                    @if (!esProveedor) { <td>—</td> }
                    <td>{{ l.coleccion }}</td><td class="right nowrap">{{ l.precio_base | bs }}</td>
                    <td><span class="badge warn">Pendiente de enviar</span><div class="muted small">Se enviará sola al volver la conexión.</div></td>
                    <td class="actions">@if (cola.puedeDeshacer(l.op)) { <button type="button" class="btn sm danger" (click)="cola.deshacer(l.op)">Deshacer</button> }</td>
                  </tr>
                }
                @for (p of propuestas(); track p.id) {
                  <tr>
                    <td><strong>{{ p.nombre }}</strong><div class="muted small">{{ p.material }}</div></td>
                    @if (!esProveedor) { <td>{{ p.proveedor }}</td> }
                    <td>{{ p.coleccion }}</td><td class="right nowrap">{{ p.precio_base | bs }}</td>
                    <td><span class="badge" [class.warn]="p.estado === 'PENDIENTE'" [class.ok]="p.estado === 'APROBADA'" [class.danger]="p.estado === 'RECHAZADA'">{{ p.estado === 'PENDIENTE' ? 'Pendiente' : p.estado === 'APROBADA' ? 'Aprobada' : 'Rechazada' }}</span>
                      @if (p.notas_revision) { <div class="muted small">{{ p.notas_revision }}</div> }</td>
                    <td class="actions">@if (!esProveedor && p.estado === 'PENDIENTE') { <button class="btn sm" (click)="revisar.set(p); notas = ''; error.set('')">Revisar</button> }</td>
                  </tr>
                }
              </tbody>
            </table>
          }
        </div>
        @if (!esProveedor) { <p class="muted small" style="margin-top:.6rem">Al aprobar una propuesta, cree el producto en «Productos» con sus tallas y colores.</p> }
      }
    </div>

    @if (detalle(); as l) {
      <div class="overlay" (click)="detalle.set(null)">
        <div class="modal" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
          <header><h2>{{ l.codigo }} · {{ textoEstado(l.estado) }}</h2><button type="button" class="btn sm ghost" (click)="detalle.set(null)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <p class="small muted">{{ l.proveedor }} → {{ l.sucursal }} · {{ l.referencia || 'sin referencia' }}</p>
            <div class="table-wrap"><table>
              <thead><tr><th>SKU</th><th>Producto</th><th>Talla</th><th>Color</th><th class="right">Enviadas</th><th class="right">Recibidas</th></tr></thead>
              <tbody>@for (i of l.items; track i.id) { <tr><td><code>{{ i.sku }}</code></td><td>{{ i.producto }}</td><td>{{ i.talla }}</td><td>{{ i.color }}</td><td class="right">{{ i.cantidad }}</td><td class="right">{{ i.cantidad_recibida ?? '—' }}</td></tr> }</tbody>
            </table></div>
            @if (l.notas) { <p class="small">{{ l.notas }}</p> }
          </div>
        </div>
      </div>
    }

    @if (modalAviso()) {
      <div class="overlay" (click)="modalAviso.set(false)">
        <form class="modal" (click)="$event.stopPropagation()" (ngSubmit)="enviarAviso()" role="dialog" aria-modal="true" style="width:min(820px,100%)">
          <header><h2>Nuevo aviso de remisión</h2><button type="button" class="btn sm ghost" (click)="modalAviso.set(false)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <div class="form-grid">
              @if (!esProveedor) { <label>Proveedor<select name="pv" [(ngModel)]="aviso.proveedor_id">@for (p of proveedores(); track p.id) { <option [ngValue]="p.id">{{ p.nombre_comercial || p.razon_social }}</option> }</select></label> }
              <label>Sucursal de destino<select name="s" [(ngModel)]="aviso.sucursal_id">@for (s of sucursales(); track s.id) { <option [ngValue]="s.id">{{ s.nombre }} · {{ s.ciudad }}</option> }</select></label>
              <label>Referencia (remisión o factura)<input name="r" [(ngModel)]="aviso.referencia" /></label>
              <label class="full">Notas<input name="n" [(ngModel)]="aviso.notas" /></label>
            </div>
            <fieldset>
              <legend>Productos del lote</legend>
              <div class="row"><input name="bq" [(ngModel)]="busqueda" placeholder="Buscar producto ya registrado por nombre o SKU…" style="flex:1" (keydown.enter)="$event.preventDefault(); buscar()" /><button necesitaInternet type="button" class="btn" (click)="buscar()">Buscar</button></div>
              @if (resultados().length) {
                <div class="resultados">@for (v of resultados(); track v.sku) { <button type="button" class="chip" (click)="agregar(v)">+ {{ v.producto }} · {{ v.talla }} · {{ v.color }} <code>{{ v.sku }}</code></button> }</div>
              }
              @if (lineas.length) {
                <div class="table-wrap" style="margin-top:.7rem"><table>
                  <thead><tr><th>SKU</th><th>Producto</th><th class="right">Cantidad</th><th class="right">Costo unit.</th><th></th></tr></thead>
                  <tbody>@for (l of lineas; track l.sku) { <tr><td><code>{{ l.sku }}</code></td><td>{{ l.producto }} · {{ l.talla }} · {{ l.color }}</td>
                    <td><input type="number" min="1" [(ngModel)]="l.cantidad" [name]="'c' + l.sku" style="width:6rem;margin-left:auto;display:block" /></td>
                    <td><input type="number" min="0" step="0.01" [(ngModel)]="l.costo" [name]="'k' + l.sku" style="width:6rem;margin-left:auto;display:block" /></td>
                    <td class="actions"><button type="button" class="btn sm danger" (click)="quitar(l)">Quitar</button></td></tr> }</tbody>
                </table></div>
              } @else { <p class="muted small" style="margin-top:.6rem">Busque y agregue al menos un producto.</p> }
            </fieldset>
            @if (error()) { <app-error [texto]="error()" /> }
          </div>
          <footer><button type="button" class="btn" (click)="modalAviso.set(false)">Cancelar</button><button class="btn primary" [disabled]="guardando() || !lineas.length || !aviso.sucursal_id">Confirmar y enviar</button></footer>
        </form>
      </div>
    }

    @if (modalPropuesta()) {
      <div class="overlay" (click)="modalPropuesta.set(false)">
        <form class="modal" (click)="$event.stopPropagation()" (ngSubmit)="enviarPropuesta()" #f="ngForm" role="dialog" aria-modal="true">
          <header><h2>Nueva propuesta de producto</h2><button type="button" class="btn sm ghost" (click)="modalPropuesta.set(false)" aria-label="Cerrar">✕</button></header>
          <div class="body"><div class="form-grid">
            <label class="full">Nombre<input name="n" [(ngModel)]="propuesta.nombre" required minlength="2" /></label>
            <label class="full">Descripción<textarea name="d" rows="2" [(ngModel)]="propuesta.descripcion"></textarea></label>
            <label>Colección<select name="c" [(ngModel)]="propuesta.coleccion_id" required>@for (c of colecciones(); track c.id) { <option [ngValue]="c.id">{{ c.nombre }} · {{ c.temporada }}</option> }</select></label>
            <label>Género<select name="g" [(ngModel)]="propuesta.genero">@for (g of generos; track g.valor) { <option [ngValue]="g.valor">{{ g.texto }}</option> }</select></label>
            <label>Precio base (Bs)<input name="p" type="number" min="0" step="0.01" [(ngModel)]="propuesta.precio_base" required /></label>
            <label>Material<input name="m" [(ngModel)]="propuesta.material" /></label>
          </div>
          @if (error()) { <app-error [texto]="error()" /> }</div>
          <footer><button type="button" class="btn" (click)="modalPropuesta.set(false)">Cancelar</button><button class="btn primary" [disabled]="guardando() || !f.valid">Enviar propuesta</button></footer>
        </form>
      </div>
    }

    @if (revisar(); as p) {
      <div class="overlay" (click)="revisar.set(null)">
        <div class="modal" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
          <header><h2>Revisar propuesta</h2><button type="button" class="btn sm ghost" (click)="revisar.set(null)" aria-label="Cerrar">✕</button></header>
          <div class="body">
            <p><strong>{{ p.nombre }}</strong> · {{ p.proveedor }} · {{ p.coleccion }} · {{ p.precio_base | bs }}</p>
            <p class="small muted">{{ p.descripcion }}</p>
            <label>Notas de la revisión <span class="hint">(obligatorias para rechazar)</span><textarea rows="3" [(ngModel)]="notas" name="notas"></textarea></label>
            @if (error()) { <app-error [texto]="error()" /> }
          </div>
          <footer><button class="btn danger" (click)="resolver(p, false)">Rechazar</button><button class="btn primary" (click)="resolver(p, true)">Aprobar</button></footer>
        </div>
      </div>
    }`,
  styles: `.resultados { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .6rem; max-height: 9rem; overflow: auto; } code { font-size: .8rem; background: #f1eee9; padding: .05rem .35rem; border-radius: 5px; }`,
})
export class AbastecimientoPage implements OnInit {
  private api = inject(ProveedoresApi);
  private catalogo = inject(CatalogoAdminApi);
  private toast = inject(ToastService);
  readonly esProveedor = inject(AuthService).rol() === ROL.PROVEEDOR;

  readonly generos = GENEROS;
  readonly pestana = signal<Pestana>('avisos');
  readonly lotes = signal<Lote[]>([]);
  readonly propuestas = signal<Propuesta[]>([]);
  readonly resumen = signal<ResumenAbastecimiento | null>(null);
  readonly proveedores = signal<Proveedor[]>([]);
  readonly sucursales = signal<SucursalDestino[]>([]);
  readonly colecciones = signal<Coleccion[]>([]);
  readonly resultados = signal<VarianteHabilitada[]>([]);
  readonly detalle = signal<Lote | null>(null);
  readonly revisar = signal<Propuesta | null>(null);
  readonly modalAviso = signal(false);
  readonly modalPropuesta = signal(false);
  readonly guardando = signal(false);
  private readonly red = inject(ConnectivityService);
  readonly cola = inject(ColaOperacionesService);
  /** Propuestas guardadas sin conexión que todavía no se enviaron: se ven en la lista como «Pendiente de enviar». */
  readonly propuestasLocales = computed(() => this.cola.operaciones().filter((o) => o.tipo === 'PROPUESTA_PROVEEDOR' && ['REGISTRADA_LOCAL', 'ENVIADA'].includes(o.estado)).map((o) => {
    const p = o.payload as { nombre?: string; material?: string; coleccion_id?: number; precio_base?: string };
    return { op: o, nombre: p.nombre ?? '', material: p.material ?? '', coleccion: this.colecciones().find((c) => c.id === p.coleccion_id)?.nombre ?? '', precio_base: p.precio_base ?? '0' };
  }));
  readonly error = signal('');
  readonly textoEstado = (e: string) => ({ EN_TRANSITO: 'En tránsito', RECIBIDO: 'Recibido', CANCELADO: 'Cancelado' } as Record<string, string>)[e] ?? e;
  aviso: any = {}; lineas: Linea[] = []; busqueda = '';
  propuesta: any = {}; notas = '';

  private readonly recargaAlVolverLaRed = this.cola.alRefrescar(() => this.cargar());  // al volver la red la pantalla se recarga sola

  ngOnInit() {
    this.cargar();
    const sinAviso = () => undefined;  // sin conexión y sin copia guardada, estas listas auxiliares quedan vacías
    this.api.sucursalesDestino().subscribe({ next: (r) => this.sucursales.set(r), error: sinAviso });
    this.catalogo.colecciones().subscribe({ next: (r) => this.colecciones.set(r), error: sinAviso });
    if (!this.esProveedor) this.api.proveedores({ solo_activos: true }).subscribe({ next: (r) => this.proveedores.set(r), error: sinAviso });
  }

  cargar() {
    this.api.lotes().subscribe({ next: (r) => this.lotes.set(r), error: (e) => { if (e.status !== 0) this.toast.error(mensajeError(e)); } });
    this.api.propuestas().subscribe({ next: (r) => this.propuestas.set(r), error: (e) => { if (e.status !== 0) this.toast.error(mensajeError(e)); } });
    if (!this.esProveedor) this.api.resumen().subscribe({ next: (r) => this.resumen.set(r), error: () => undefined });
  }

  // ---- aviso de remisión ----
  abrirAviso() {
    this.aviso = { proveedor_id: this.proveedores()[0]?.id ?? null, sucursal_id: this.sucursales()[0]?.id ?? null, referencia: '', notas: '' };
    this.lineas = []; this.busqueda = ''; this.resultados.set([]); this.error.set(''); this.modalAviso.set(true);
    this.buscar();
  }
  buscar() { this.api.variantes(this.busqueda.trim()).subscribe({ next: (r) => this.resultados.set(r), error: () => undefined }); }
  agregar(v: VarianteHabilitada) {
    const existente = this.lineas.find((l) => l.sku === v.sku);
    if (existente) existente.cantidad++; else this.lineas.push({ ...v, cantidad: 1, costo: null });
  }
  quitar(l: Linea) { this.lineas = this.lineas.filter((x) => x !== l); }

  enviarAviso() {
    this.guardando.set(true); this.error.set('');
    const cuerpo = {
      sucursal_id: this.aviso.sucursal_id, proveedor_id: this.esProveedor ? null : this.aviso.proveedor_id, referencia: this.aviso.referencia, notas: this.aviso.notas,
      items: this.lineas.map((l) => ({ sku: l.sku, cantidad: l.cantidad, costo_unitario: l.costo || null })),
    };
    this.api.crearLote(cuerpo).subscribe({
      next: (l) => { this.guardando.set(false); this.modalAviso.set(false); this.toast.ok(`Aviso ${l.codigo} enviado: el lote queda en tránsito.`); this.cargar(); },
      error: (e) => { this.guardando.set(false); this.error.set(mensajeError(e)); },
    });
  }

  cancelar(l: Lote) {
    if (!confirm(`¿Cancelar el lote ${l.codigo}?`)) return;
    this.api.cancelarLote(l.id).subscribe({ next: () => { this.toast.ok('Lote cancelado.'); this.cargar(); }, error: (e) => this.toast.error(mensajeError(e)) });
  }

  // ---- propuestas ----
  abrirPropuesta() { this.propuesta = { nombre: '', descripcion: '', coleccion_id: this.colecciones()[0]?.id ?? null, genero: 'UNISEX', precio_base: null, material: '' }; this.error.set(''); this.modalPropuesta.set(true); }
  /** Con Internet va directo; sin conexión (B9) queda en la cola del dispositivo con las mismas validaciones y se envía sola al recuperar la red. */
  async enviarPropuesta() {
    this.error.set('');
    if (!this.red.online()) { await this.guardarSinConexion(); return; }
    this.guardando.set(true);
    this.api.crearPropuesta(this.propuesta).subscribe({
      next: () => { this.guardando.set(false); this.modalPropuesta.set(false); this.toast.ok('Propuesta enviada a la administración.'); this.cargar(); },
      error: (e) => { this.guardando.set(false); if (e?.status === 0) void this.guardarSinConexion(); else this.error.set(mensajeError(e)); },
    });
  }

  private async guardarSinConexion() {
    await this.cola.registrar('PROPUESTA_PROVEEDOR', { ...this.propuesta, precio_base: String(this.propuesta.precio_base ?? 0) }, null, `Propuesta de producto: ${this.propuesta.nombre}`);
    this.guardando.set(false); this.modalPropuesta.set(false);
    this.toast.ok('Propuesta guardada en este dispositivo. Se enviará sola al recuperar la conexión.');
  }
  resolver(p: Propuesta, aprobar: boolean) {
    this.error.set('');
    (aprobar ? this.api.aprobarPropuesta(p.id, this.notas) : this.api.rechazarPropuesta(p.id, this.notas)).subscribe({
      next: () => { this.revisar.set(null); this.toast.ok(aprobar ? 'Propuesta aprobada.' : 'Propuesta rechazada.'); this.cargar(); },
      error: (e) => this.error.set(mensajeError(e)),
    });
  }
}
