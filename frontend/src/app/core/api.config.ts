/** URL base del backend. En desarrollo apunta a FastAPI en localhost:8000; en la nube se sirve tras Nginx en /api. */
const w = window as unknown as { __API_URL__?: string };
const local = ['localhost', '127.0.0.1'].includes(location.hostname);
export const API_URL: string = w.__API_URL__ ?? (local ? `http://${location.hostname}:8000/api` : '/api');
/** Origen del backend: de aquí cuelgan las imágenes de productos (`/media/...`). */
export const MEDIA_URL: string = API_URL.replace(/\/api$/, '');
