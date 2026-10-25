export type Rol = 'SuperAdministrador' | 'Administrador' | 'Encargado' | 'Cajero' | 'Cliente';
export const ROL = {
  SUPER: 'SuperAdministrador' as Rol,
  ADMIN: 'Administrador' as Rol,
  ENCARGADO: 'Encargado' as Rol,
  CAJERO: 'Cajero' as Rol,
  CLIENTE: 'Cliente' as Rol,
};

export interface UsuarioSesion { id: number; nombre: string; apellidos: string; email: string; rol: Rol; sucursal_id: number | null; sucursal_nombre: string | null; }
export interface EmpresaSesion { id: number; codigo: string; razon_social: string; estado: string; }
export interface PlanSesion { nombre: string; max_sucursales: number; reportes_ia: boolean; offline: boolean; reportes_convencionales: boolean; }
export interface SuscripcionSesion { estado: string; fecha_inicio: string; fecha_vencimiento: string; plan: PlanSesion; }
export interface Sesion { usuario: UsuarioSesion; empresa: EmpresaSesion | null; suscripcion: SuscripcionSesion | null; panel: string; restringido: boolean; }
export interface TokenResponse extends Sesion { access_token: string; refresh_token: string; token_type: string; }
export interface LoginBody { codigo_empresa: string | null; email: string; password: string; }

export interface Plan {
  id: number; nombre: string; descripcion: string | null; precio: string | number; periodicidad: string; max_sucursales: number;
  reportes_ia: boolean; offline: boolean; reportes_convencionales: boolean; activo: boolean; empresas_suscritas: number;
}
export interface EmpresaExcedida { empresa_id: number; codigo: string; sucursales_activas: number; limite: number; }
export interface PlanGuardado { plan: Plan; advertencias: EmpresaExcedida[]; }

export interface Empresa {
  id: number; codigo: string; razon_social: string; nit: string; email_contacto: string | null; telefono: string | null;
  estado: string; creado_en: string; plan: string | null; suscripcion_estado: string | null; fecha_vencimiento: string | null;
  administrador_email?: string | null;
}
export interface PlanResumen { id: number; nombre: string; max_sucursales: number; reportes_ia: boolean; offline: boolean; reportes_convencionales: boolean; }
export interface Suscripcion { id: number; empresa_id: number; plan: PlanResumen; fecha_inicio: string; fecha_vencimiento: string; estado: string; forma_pago: string | null; monto: string | number | null; }
export interface SuscripcionDetalle { vigente: Suscripcion | null; historial: Suscripcion[]; uso: { sucursales_activas: number; limite: number | null }; }

export interface Usuario { id: number; nombre: string; apellidos: string; email: string; rol: Rol; sucursal_id: number | null; sucursal_nombre: string | null; activo: boolean; ultimo_acceso: string | null; }
export interface Ciudad { id: number; nombre: string; departamento: string | null; }
export interface Sucursal { id: number; nombre: string; ciudad_id: number; ciudad: string; direccion: string | null; telefono: string | null; horario: string | null; activa: boolean; }
export interface UsoPlan { plan: string | null; activas: number; limite: number | null; disponibles: number | null; }
export interface SucursalesRespuesta { uso_plan: UsoPlan; sucursales: Sucursal[]; }
