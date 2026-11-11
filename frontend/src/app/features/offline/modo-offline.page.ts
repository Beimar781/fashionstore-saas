import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { ColaOperacionesService } from '../../core/offline/cola-operaciones.service';
import { ConnectivityService } from '../../core/offline/connectivity.service';
import { CatalogoLocalComponent } from './catalogo-local.component';
import { DemostracionComponent } from './demostracion.component';
import { OperacionesLocalesComponent } from './operaciones.component';
import { RegistrarOfflineComponent } from './registrar-offline.component';
import { RegistroSyncComponent } from './registro-sync.component';
import { ResumenTurnoComponent } from './resumen-turno.component';
import { TareasSucursalComponent } from './tareas-sucursal.component';

type Pestana = 'catalogo' | 'registrar' | 'operaciones' | 'registro' | 'turno' | 'tareas' | 'demo';

/** Operación sin conexión (RF18 a RF21): catálogo descargado, registro de ventas de contado o reservas y cola de operaciones con su sincronización. */
@Component({
  selector: 'app-modo-offline',
  imports: [DemostracionComponent, CatalogoLocalComponent, RegistrarOfflineComponent, OperacionesLocalesComponent, RegistroSyncComponent, ResumenTurnoComponent, TareasSucursalComponent],
  template: `
    <div class="page">
      <div class="page-head"><div><h1>Modo sin conexión</h1><p>Descargue el catálogo, registre ventas de contado o reservas aunque no haya Internet y sincronícelas cuando vuelva.</p></div>
        <span class="badge" [class.ok]="red.online()" [class.warn]="!red.online()">{{ red.online() ? 'Con conexión' : 'Sin conexión' }}</span></div>
      <div class="tabs" role="tablist">
        <button role="tab" [class.activa]="pestana() === 'catalogo'" (click)="pestana.set('catalogo')">Catálogo</button>
        <button role="tab" [class.activa]="pestana() === 'registrar'" (click)="pestana.set('registrar')">Registrar</button>
        <button role="tab" [class.activa]="pestana() === 'operaciones'" (click)="pestana.set('operaciones')">Operaciones @if (cola.pendientes().length) { <span class="badge warn">{{ cola.pendientes().length }}</span> }</button>
        @if (!esCliente) { <button role="tab" [class.activa]="pestana() === 'tareas'" (click)="pestana.set('tareas')">Tareas de la sucursal</button><button role="tab" [class.activa]="pestana() === 'turno'" (click)="pestana.set('turno')">Mi turno</button> }
        <button role="tab" [class.activa]="pestana() === 'registro'" (click)="pestana.set('registro')">Registro</button>
        <button role="tab" [class.activa]="pestana() === 'demo'" (click)="pestana.set('demo')">Demostración</button>
      </div>
      @switch (pestana()) {
        @case ('catalogo') { <app-catalogo-local /> }
        @case ('registrar') { <app-registrar-offline /> }
        @case ('operaciones') { <app-operaciones-locales /> }
        @case ('registro') { <app-registro-sync /> }
        @case ('turno') { <app-resumen-turno /> }
        @case ('tareas') { <app-tareas-sucursal /> }
        @case ('demo') { <app-demostracion /> }
      }
    </div>`,
})
export class ModoOfflinePage {
  readonly red = inject(ConnectivityService);
  readonly cola = inject(ColaOperacionesService);
  // el indicador de la barra superior abre directo en «Operaciones» (?pestana=operaciones)
  readonly pestana = signal<Pestana>((inject(ActivatedRoute).snapshot.queryParamMap.get('pestana') as Pestana | null) ?? 'catalogo');
  readonly esCliente = inject(AuthService).rol() === 'Cliente';
}
