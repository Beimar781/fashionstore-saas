import { ROL } from '../models';

/** Dónde ve cada rol su cola de operaciones y el detalle de lo que se sincronizó (el panel de diagnóstico; el Administrador, sus conflictos; el Proveedor, sus propuestas). */
export function rutaDeLaCola(rol: string | null | undefined): string | null {
  switch (rol) {
    case ROL.CLIENTE: return '/tienda/offline?pestana=operaciones';
    case ROL.CAJERO: return '/pos/offline?pestana=operaciones';
    case ROL.ENCARGADO: return '/sucursal/offline?pestana=operaciones';
    case ROL.ADMIN: return '/empresa/conflictos';
    case ROL.PROVEEDOR: return '/proveedor';
    default: return null;
  }
}
