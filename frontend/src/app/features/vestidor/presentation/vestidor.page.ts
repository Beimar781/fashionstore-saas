import { Component, ElementRef, OnDestroy, OnInit, ViewChild, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MEDIA_URL } from '../../../core/api.config';
import { VestidorApi } from '../../../core/api/vestidor.api';
import { CatalogoApi } from '../../../core/api/catalogo.api';
import { ComprasApi } from '../../../core/api/compras.api';
import { CarritoEstadoService } from '../../../core/carrito/carrito-estado.service';
import { AuthService } from '../../../core/auth/auth.service';
import { ROL } from '../../../core/models';
import { ToastService, mensajeError } from '../../../core/ui/toast.service';
import { Anclaje, colocarPrenda } from '../domain/anclaje';
import { BloqueoPose, mensajesGuia, PoseCuerpo } from '../domain/cuerpo';
import { FiltroPose } from '../domain/filtro-one-euro';
import { ColorVestidor, VestidorProducto } from '../../../core/vestidor.models';
import { Opciones } from '../../../core/catalogo.models';

@Component({
  selector: 'app-vestidor-web',
  imports: [FormsModule, RouterLink],
  template: `<main class="page">
    <a class="small" [routerLink]="['/tienda/catalogo', id]">← Volver a la prenda</a>
    @if (cargando()) {
      <p>Cargando vestidor…</p>
    } @else if (error()) {
      <div class="alert danger" role="alert">{{ error() }}</div>
    } @else if (producto(); as p) {
      <h1
        #titulo
        (pointerdown)="iniciarPulsacion()"
        (pointerup)="terminarPulsacion()"
        (pointerleave)="terminarPulsacion()"
      >
        Vestidor virtual · {{ p.producto }}
      </h1>
      @if (!p.admite || !colores.length) {
        <div class="alert warn">
          {{ p.mensaje || 'Esta prenda no tiene imágenes listas para el vestidor.' }}
        </div>
      } @else {
        <section class="vestidor">
          <div class="escena">
            <video #video autoplay muted playsinline></video><canvas #canvas></canvas>
            @if (camaraError()) {
              <div class="aviso">{{ camaraError() }}</div>
            }
            @if (camaraActiva()) {
              <div class="guia">{{ guia() }}</div>
            }
            @if (fpsVisible()) {
              <small class="fps">{{ fps() }} FPS</small>
            }
          </div>
          <div class="controles">
            <label
              >Color<select [ngModel]="colorId()" (ngModelChange)="elegirColor($event)">
                @for (c of colores; track c.color_id) {
                  <option [ngValue]="c.color_id">{{ c.color }}</option>
                }
              </select></label
            >
            <label
              >Talla<select [ngModel]="talla()" (ngModelChange)="elegirTalla($event)">
                @for (t of tallas; track t) {
                  <option [value]="t">{{ t }}</option>
                }
              </select></label
            >
            @if (!camaraActiva()) {
              <button class="btn primary" (click)="abrirCamara()">Activar cámara</button>
            }
            <button class="btn" (click)="tomarFoto()" [disabled]="!camaraActiva()">
              Tomar foto
            </button>
            <button
              class="btn primary"
              (click)="agregarCarrito()"
              [disabled]="!varianteId() || !sucursalParaCarrito()"
            >
              Agregar al carrito
            </button>
            @if (offlineSinRecurso()) {
              <p class="alert warn">
                Descargue el catálogo con conexión para usar el vestidor sin Internet.
              </p>
            }
            <p class="small muted">
              La cámara se procesa en este dispositivo. El video no se envía al servidor.
            </p>
          </div>
        </section>
      }
    }
  </main>`,
  styles: `
    h1 {
      user-select: none;
    }
    .vestidor {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 260px;
      gap: 1rem;
    }
    .escena {
      position: relative;
      background: #111;
      min-height: 480px;
      overflow: hidden;
      border-radius: 12px;
      aspect-ratio: 4/3;
    }
    .escena video,
    .escena canvas {
      position: absolute;
      width: 100%;
      height: 100%;
      inset: 0;
      object-fit: contain;
    }
    .escena video {
      transform: scaleX(-1);
    }
    .guia,
    .aviso,
    .fps {
      position: absolute;
      background: #000b;
      color: white;
      padding: 0.55rem 0.8rem;
      border-radius: 8px;
    }
    .guia {
      left: 50%;
      bottom: 1rem;
      transform: translateX(-50%);
    }
    .aviso {
      inset: 45% 10% auto;
      text-align: center;
    }
    .fps {
      top: 0.5rem;
      right: 0.5rem;
    }
    .controles {
      display: flex;
      flex-direction: column;
      gap: 0.8rem;
    }
    .controles select {
      display: block;
      width: 100%;
    }
    @media (max-width: 760px) {
      .vestidor {
        grid-template-columns: 1fr;
      }
      .escena {
        min-height: 300px;
      }
    }
  `,
})
export class VestidorPage implements OnInit, OnDestroy {
  @ViewChild('video') private videoRef?: ElementRef<HTMLVideoElement>;
  @ViewChild('canvas') private canvasRef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('titulo') private tituloRef?: ElementRef<HTMLElement>;
  private route = inject(ActivatedRoute);
  private vestidorApi = inject(VestidorApi);
  private catalogo = inject(CatalogoApi);
  private compras = inject(ComprasApi);
  private carrito = inject(CarritoEstadoService);
  private auth = inject(AuthService);
  private toast = inject(ToastService);
  readonly media = MEDIA_URL;
  readonly id = Number(this.route.snapshot.paramMap.get('id'));
  readonly producto = signal<VestidorProducto | null>(null);
  readonly cargando = signal(true);
  readonly error = signal('');
  readonly camaraError = signal('');
  readonly camaraActiva = signal(false);
  readonly colorId = signal<number | null>(null);
  readonly talla = signal('');
  readonly guia = signal(mensajesGuia.sinPersona);
  readonly fpsVisible = signal(false);
  readonly fps = signal(0);
  readonly offlineSinRecurso = signal(false);
  private sucursalId = this.route.snapshot.queryParamMap.get('sucursal')
    ? Number(this.route.snapshot.queryParamMap.get('sucursal'))
    : null;
  private stream: MediaStream | null = null;
  private landmarker: import('@mediapipe/tasks-vision').PoseLandmarker | null = null;
  private imagen: HTMLImageElement | null = null;
  private frame = 0;
  private ultimoFps = 0;
  private framesFps = 0;
  private pulsacion: ReturnType<typeof setTimeout> | null = null;
  private bloqueo = new BloqueoPose();
  private filtro = new FiltroPose();
  private ultimaPose: PoseCuerpo | null = null;
  private poseLatenciaMs = 0;
  private el(): { image: HTMLImageElement; anclaje: Anclaje; ratio: number } | null {
    const c = this.producto()?.colores.find((x) => x.color_id === this.colorId());
    return c?.listo && c.imagen_url && c.anclaje && this.imagen
      ? { image: this.imagen, anclaje: c.anclaje, ratio: (c.ancho ?? 1) / (c.alto ?? 1) }
      : null;
  }
  get colores(): ColorVestidor[] {
    return this.producto()?.colores.filter((c) => c.listo) ?? [];
  }
  get tallas() {
    return Object.keys(this.producto()?.escala_tallas ?? {}).sort();
  }
  readonly varianteId = signal<number | null>(null);
  private opciones: Opciones | null = null;

  ngOnInit() {
    if (this.auth.rol() !== ROL.CLIENTE) {
      this.error.set('Esta función está disponible para Clientes.');
      this.cargando.set(false);
      return;
    }
    this.vestidorApi.producto(this.id).subscribe({
      next: (p) => {
        this.producto.set(p);
        this.cargando.set(false);
        const listo = p.colores.find((c) => c.listo);
        this.colorId.set(listo?.color_id ?? null);
        this.talla.set(Object.keys(p.escala_tallas).sort()[0] ?? '');
        this.actualizarVariante();
        if (listo) void this.cargarImagen(listo);
      },
      error: (e) => {
        this.error.set(mensajeError(e));
        this.cargando.set(false);
      },
    });
    this.catalogo.opciones(this.id, this.sucursalId).subscribe({
      next: (o) => {
        this.opciones = o;
        const v =
          o.variantes.find((x) => x.color_id === this.colorId() && x.disponible) ??
          o.variantes.find(
            (x) =>
              x.disponible &&
              this.producto()?.colores.some((c) => c.color_id === x.color_id && c.listo),
          );
        if (v) {
          this.talla.set(v.talla);
          this.colorId.set(v.color_id);
          this.actualizarVariante();
        }
      },
      error: () => undefined,
    });
    document.addEventListener('visibilitychange', this.alCambiarVisibilidad);
  }
  private alCambiarVisibilidad = () => {
    if (document.hidden) this.cerrarCamara();
  };
  private async cargarImagen(c: ColorVestidor) {
    if (!c.imagen_url) return;
    try {
      const url = /^https?:/.test(c.imagen_url) ? c.imagen_url : this.media + c.imagen_url;
      this.imagen = await this.obtenerImagen(url);
    } catch {
      this.offlineSinRecurso.set(!navigator.onLine);
    }
  }
  private async obtenerImagen(url: string): Promise<HTMLImageElement> {
    const cache = await caches.open('vestidor-productos');
    let response = await cache.match(url);
    if (!response) {
      if (!navigator.onLine) throw Error();
      response = await fetch(url);
      if (!response.ok) throw Error();
      await cache.put(url, response.clone());
    }
    const blob = await response.blob(),
      objectUrl = URL.createObjectURL(blob),
      img = new Image();
    img.src = objectUrl;
    await img.decode();
    return img;
  }
  async elegirColor(id: number) {
    this.colorId.set(id);
    const c = this.producto()?.colores.find((x) => x.color_id === id);
    if (c) await this.cargarImagen(c);
    this.actualizarVariante();
    this.reiniciar();
  }
  elegirTalla(t: string) {
    this.talla.set(t);
    this.actualizarVariante();
    this.dibujar();
  }
  private actualizarVariante() {
    const id = this.colorId(),
      t = this.talla();
    const v = this.opciones?.variantes.find(
      (x) => x.color_id === id && x.talla === t && x.disponible,
    );
    this.varianteId.set(v?.variante_id ?? null);
  }
  async abrirCamara() {
    this.camaraError.set('');
    if (!navigator.mediaDevices?.getUserMedia) {
      this.camaraError.set(
        'Este navegador no admite el vestidor virtual. Pruebe con Chrome o Edge.',
      );
      return;
    }
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user' },
        audio: false,
      });
      const v = this.videoRef!.nativeElement;
      v.srcObject = this.stream;
      await v.play();
      if (!this.landmarker) {
        try {
          const vision = await import('@mediapipe/tasks-vision');
          const wasm = await vision.FilesetResolver.forVisionTasks('/mediapipe/wasm');
          this.landmarker = await vision.PoseLandmarker.createFromOptions(wasm, {
            baseOptions: {
              modelAssetPath: '/mediapipe/pose_landmarker_lite.task',
              delegate: 'CPU',
            },
            runningMode: 'VIDEO',
            numPoses: 1,
            minPoseDetectionConfidence: 0.3,
            minPosePresenceConfidence: 0.3,
            minTrackingConfidence: 0.3,
          });
        } catch {
          if (!navigator.onLine) {
            this.offlineSinRecurso.set(true);
            this.camaraError.set('');
          } else this.camaraError.set('No se pudo cargar el modelo del vestidor.');
          this.cerrarCamara();
          return;
        }
      }
      this.camaraActiva.set(true);
      this.ultimoFps = performance.now();
      this.bucle();
    } catch (e) {
      const n = (e as DOMException).name;
      this.camaraError.set(
        n === 'NotAllowedError' || n === 'SecurityError'
          ? 'Permita el acceso a la cámara para usar el vestidor.'
          : n === 'NotFoundError' || n === 'DevicesNotFoundError'
            ? 'Este dispositivo no tiene cámara disponible.'
            : 'Este navegador no admite el vestidor virtual. Pruebe con Chrome o Edge.',
      );
      this.cerrarCamara();
    }
  }
  private bucle = () => {
    if (!this.camaraActiva() || document.hidden) return;
    const v = this.videoRef!.nativeElement,
      c = this.canvasRef!.nativeElement;
    if (v.videoWidth) {
      if (c.width !== v.videoWidth || c.height !== v.videoHeight) {
        c.width = v.videoWidth;
        c.height = v.videoHeight;
        this.bloqueo = new BloqueoPose(proportion(v.videoWidth, v.videoHeight));
      }
      const inicio = performance.now();
      const resultado = this.landmarker!.detectForVideo(v, inicio);
      this.poseLatenciaMs = performance.now() - inicio;
      const puntos = resultado.landmarks?.[0];
      let pose: PoseCuerpo | null = null;
      if (puntos) {
        const punto = (i: number) => ({
          x: 1 - puntos[i].x,
          y: puntos[i].y,
          confianza: puntos[i].visibility ?? 0,
        });
        pose = {
          hombroIzq: punto(11),
          hombroDer: punto(12),
          caderaIzq: punto(23),
          caderaDer: punto(24),
        };
        pose = this.filtro.filtrar(pose, inicio / 1000);
      }
      this.bloqueo.registrar(pose);
      if (pose) this.ultimaPose = pose;
      else if (!this.bloqueo.bloqueado) this.filtro.reiniciar();
      this.guia.set(mensajesGuia[this.bloqueo.ultimaGuia]);
      this.dibujar();
      if (this.fpsVisible()) {
        this.framesFps++;
        if (inicio - this.ultimoFps >= 1000) {
          this.fps.set(this.framesFps);
          this.framesFps = 0;
          this.ultimoFps = inicio;
        }
      }
    }
    this.frame = requestAnimationFrame(this.bucle);
  };
  private dibujar() {
    const canvas = this.canvasRef!.nativeElement,
      ctx = canvas.getContext('2d')!,
      r = this.el();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const p = this.ultimaPose;
    if (!r || !p || !this.bloqueo.bloqueado) return;
    const x = colocarPrenda(
      p,
      r.anclaje,
      this.escalaTalla(),
      { width: canvas.width, height: canvas.height },
      r.ratio,
    );
    ctx.save();
    ctx.translate(x.centroX, x.centroY);
    ctx.rotate(x.angulo);
    ctx.drawImage(r.image, -x.ancho / 2, -x.alto / 2, x.ancho, x.alto);
    ctx.restore();
  }
  private escalaTalla() {
    const escalas = this.producto()?.escala_tallas ?? {};
    const talla = this.talla();
    return escalas[talla.trim().toUpperCase()] ?? escalas[talla] ?? 1;
  }
  private reiniciar() {
    this.bloqueo.reiniciar();
    this.filtro.reiniciar();
    this.ultimaPose = null;
    this.dibujar();
  }
  tomarFoto() {
    const v = this.videoRef!.nativeElement,
      c = this.canvasRef!.nativeElement,
      out = document.createElement('canvas');
    out.width = v.videoWidth;
    out.height = v.videoHeight;
    const ctx = out.getContext('2d')!;
    ctx.translate(out.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(v, 0, 0);
    ctx.drawImage(c, 0, 0);
    const a = document.createElement('a');
    a.download = `vestidor-${this.id}.png`;
    a.href = out.toDataURL('image/png');
    a.click();
  }
  agregarCarrito() {
    const id = this.varianteId();
    if (!id) return;
    this.compras.agregar(id, 1, this.sucursalParaCarrito()).subscribe({
      next: (c) => {
        this.carrito.fijar(c);
        this.toast.ok('Prenda agregada al carrito.');
      },
      error: (e) => this.toast.error(mensajeError(e)),
    });
  }
  sucursalParaCarrito() {
    return this.carrito.total() > 0
      ? this.carrito.sucursalId()
      : (this.sucursalId ?? this.carrito.sucursalId());
  }
  iniciarPulsacion() {
    this.pulsacion = setTimeout(() => this.fpsVisible.update((v) => !v), 700);
  }
  terminarPulsacion() {
    if (this.pulsacion) clearTimeout(this.pulsacion);
  }
  private cerrarCamara() {
    cancelAnimationFrame(this.frame);
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.camaraActiva.set(false);
  }
  ngOnDestroy() {
    this.cerrarCamara();
    document.removeEventListener('visibilitychange', this.alCambiarVisibilidad);
    this.landmarker?.close();
  }
}
function proportion(w: number, h: number) {
  return w / h;
}
