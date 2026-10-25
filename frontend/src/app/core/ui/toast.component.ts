import { Component, inject } from '@angular/core';
import { ToastService } from './toast.service';

@Component({
  selector: 'app-toasts',
  template: `
    <div class="wrap" aria-live="polite">
      @for (t of toast.toasts(); track t.id) {
        <div class="t {{ t.tipo }}" role="status">{{ t.texto }}</div>
      }
    </div>`,
  styles: `
    .wrap { position: fixed; right: 1rem; bottom: 1rem; display: grid; gap: .5rem; z-index: 100; max-width: min(420px, calc(100vw - 2rem)); }
    .t { padding: .75rem 1rem; border-radius: 10px; color: #fff; box-shadow: 0 8px 24px rgba(0,0,0,.25); font-size: .92rem; animation: in .2s ease; }
    .ok { background: #1e7a4f; } .danger { background: #b3261e; } .warn { background: #9a5b00; }
    @keyframes in { from { transform: translateY(8px); opacity: 0; } }`,
})
export class ToastComponent {
  readonly toast = inject(ToastService);
}
