import { Component, OnDestroy, OnInit, output, signal } from '@angular/core';

/** ¿El navegador sabe leer códigos de barras y QR? (BarcodeDetector: Chrome y Edge en la mayoría de equipos; si no, solo queda el campo de texto.) */
export const hayEscaner = () => 'BarcodeDetector' in window && !!navigator.mediaDevices?.getUserMedia;

/** B7 · Escáner de códigos de barras y QR con la cámara. Todo se lee en el equipo; el video no sale de él. Emite el primer código leído. */
@Component({
  selector: 'app-escaner',
  template: `
    <div class="overlay" (click)="cerrar.emit()">
      <div class="modal" (click)="$event.stopPropagation()" role="dialog" aria-modal="true" aria-label="Escanear código">
        <header><h2>Escanear código</h2><button type="button" class="btn sm ghost" (click)="cerrar.emit()" aria-label="Cerrar">✕</button></header>
        <div class="body stack">
          @if (error()) { <div class="alert danger" role="alert">{{ error() }}</div> }
          <video #video autoplay playsinline muted style="width:100%;border-radius:10px;background:#000"></video>
          <p class="small muted">Apunte al código de barras o QR de la prenda.</p>
        </div>
      </div>
    </div>`,
})
export class EscanerComponent implements OnInit, OnDestroy {
  readonly codigo = output<string>();
  readonly cerrar = output<void>();
  readonly error = signal('');
  private flujo?: MediaStream;
  private activo = true;

  async ngOnInit() {
    try {
      this.flujo = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
      const video = document.querySelector('app-escaner video') as HTMLVideoElement;
      video.srcObject = this.flujo;
      await video.play();
      const detector = new (window as any).BarcodeDetector();
      const leer = async () => {
        if (!this.activo) return;
        try {
          const lecturas = await detector.detect(video);
          if (lecturas.length) { this.activo = false; this.codigo.emit(lecturas[0].rawValue); return; }
        } catch { /* un cuadro que falla se descarta */ }
        setTimeout(leer, 250);
      };
      void leer();
    } catch (e) {
      const nombre = (e as { name?: string }).name;
      this.error.set(nombre === 'NotAllowedError' ? 'Permita el acceso a la cámara para escanear códigos.' : nombre === 'NotFoundError' ? 'Este dispositivo no tiene cámara disponible.' : 'No se pudo abrir la cámara.');
    }
  }

  ngOnDestroy() { this.activo = false; this.flujo?.getTracks().forEach((t) => t.stop()); }
}
