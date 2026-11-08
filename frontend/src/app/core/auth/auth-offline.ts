export type AccionAuthSinConexion =
  'iniciar sesión' | 'crear su cuenta' | 'recuperar su contraseña';

export function mensajeAuthSinConexion(accion: AccionAuthSinConexion): string {
  return `Sin conexión: necesita Internet para ${accion}.`;
}

export function errorDeConexion(error: unknown, online: boolean): boolean {
  return !online || (error as { status?: number } | null)?.status === 0;
}
