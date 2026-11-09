import { Injectable, signal } from '@angular/core';

/** Deja el texto del reporte listo para leerlo en voz alta: sin símbolos de formato y en frases cortas (Chrome corta las lecturas muy largas). */
export function textoParaLeer(texto: string): string[] {
  const limpio = texto.replace(/[*#_`|>~]/g, ' ').replace(/Bs\s?/g, 'bolivianos ').replace(/[ \t]+/g, ' ');
  const frases = limpio.split(/\n+|(?<=[.;:!?])\s+/).map((f) => f.trim()).filter((f) => f.length > 1);
  return frases.flatMap((f) => (f.length <= 180 ? [f] : f.match(/.{1,180}(\s|$)/g)!.map((x) => x.trim())));
}

/** Lectura en voz alta con la síntesis de voz del navegador (sin claves ni servicios externos). */
@Injectable({ providedIn: 'root' })
export class VozService {
  readonly disponible = 'speechSynthesis' in window;
  readonly hablando = signal(false);
  private numero = 0;

  /** Lee el texto; la promesa termina al acabar la lectura o al llamar a detener(). */
  hablar(texto: string): Promise<void> {
    this.detener();
    const frases = textoParaLeer(texto);
    if (!this.disponible || !frases.length) return Promise.resolve();
    const mia = ++this.numero;
    this.hablando.set(true);
    const voz = this.elegirVoz();
    return new Promise<void>((resolver) => {
      const siguiente = (i: number) => {
        if (mia !== this.numero || i >= frases.length) { if (mia === this.numero) this.hablando.set(false); resolver(); return; }
        const dicho = new SpeechSynthesisUtterance(frases[i]);
        dicho.lang = voz?.lang ?? 'es-ES';
        if (voz) dicho.voice = voz;
        dicho.onend = () => siguiente(i + 1);
        dicho.onerror = () => siguiente(frases.length);
        speechSynthesis.speak(dicho);
      };
      siguiente(0);
    });
  }

  detener() {
    this.numero++;
    if (this.disponible) speechSynthesis.cancel();
    this.hablando.set(false);
  }

  private elegirVoz(): SpeechSynthesisVoice | undefined {
    const voces = speechSynthesis.getVoices().filter((v) => v.lang.toLowerCase().startsWith('es'));
    return voces.find((v) => /es-(bo|us|mx)/i.test(v.lang)) ?? voces[0];
  }
}
