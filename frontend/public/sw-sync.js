// B10 · Service worker de la app: el de Angular más la sincronización en segundo plano.
// Cuando el navegador recupera la red dispara 'sync'; el worker avisa a las ventanas abiertas para que envíen la cola.
importScripts('./ngsw-worker.js');

self.addEventListener('sync', (evento) => {
  if (evento.tag !== 'sincronizar-cola') return;
  evento.waitUntil(
    self.clients.matchAll({ includeUncontrolled: true }).then((ventanas) => ventanas.forEach((v) => v.postMessage({ tipo: 'SINCRONIZAR_COLA' }))),
  );
});
