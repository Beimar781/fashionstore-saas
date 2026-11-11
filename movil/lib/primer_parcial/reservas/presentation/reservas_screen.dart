import 'package:flutter/material.dart';
import '../../../features/offline/data/estado_legible.dart';
import 'package:provider/provider.dart';

import '../../../core/network/api_client.dart';
import '../../../features/auth/data/auth_repository.dart';
import '../../../features/offline/presentation/modo_offline_screen.dart'
    show fechaCorta;
import '../../../features/offline/presentation/offline_controller.dart';
import '../../../features/offline/presentation/operaciones_con_problema.dart';
import '../../catalogo/presentation/catalogo_screen.dart';
import '../data/reserva_borrador.dart';
import '../data/reservas_repository.dart';
import 'mi_reserva_screen.dart';

/// Reservas del cliente (CU-10): consulta y cancelación con motivo. «Mi reserva» confirma una reserva nueva; sin conexión se reserva desde «Modo sin conexión».
class ReservasScreen extends StatefulWidget {
  const ReservasScreen({super.key, this.integrado = false});
  final bool integrado;

  @override
  State<ReservasScreen> createState() => _ReservasScreenState();
}

class _ReservasScreenState extends State<ReservasScreen> {
  late final ReservasRepository _repo =
      ReservasRepository(context.read<AuthRepository>().api);
  List<Map<String, dynamic>>? _reservas;
  String? _error;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  int? _refrescoVisto;

  Future<void> _cargar() async {
    try {
      final r = await _repo.reservas();
      final offline = context.read<OfflineController>();
      final sesion = offline.sesion;
      if (sesion?.empresaId != null) {
        await offline.repo
            .guardarReservasVistas(r, sesion!.usuarioId, sesion.empresaId!);
      }
      final combinadas = await _conPendientes(r);
      if (mounted) {
        setState(() {
          _reservas = combinadas;
          _error = null;
        });
      }
    } on ApiException catch (e) {
      final offline = context.read<OfflineController>();
      final sesion = offline.sesion;
      final vistas = sesion?.empresaId == null
          ? <Map<String, dynamic>>[]
          : await offline.repo
              .reservasVistas(sesion!.usuarioId, sesion.empresaId!);
      final locales = await _conPendientes(vistas);
      if (mounted) {
        setState(() {
          _reservas = locales;
          _error = locales.isNotEmpty
              ? null
              : (e.sinConexion
                  ? 'Sin conexión: todavía no se descargaron sus reservas.'
                  : e.mensaje);
        });
      }
    }
  }

  Future<List<Map<String, dynamic>>> _conPendientes(
      List<Map<String, dynamic>> vistas) async {
    final offline = context.read<OfflineController>();
    final sesion = offline.sesion;
    if (sesion?.empresaId == null) return vistas;
    final operaciones =
        await offline.repo.operaciones(sesion!.usuarioId, sesion.empresaId!);
    final resultado = [...vistas];
    for (final op
        in operaciones.where((o) => o.tipo == 'RESERVA' && o.pendiente)) {
      final items = (op.payload['items'] as List? ?? const [])
          .cast<Map<String, dynamic>>();
      resultado.insert(0, {
        'id': op.id,
        'codigo': op.referencia ?? 'RES-${op.id.substring(0, 8).toUpperCase()}',
        'estado': op.estado,
        'estado_local': estadoLegible(op),
        'pendiente_local': true,
        'sucursal_id': op.sucursalId,
        'sucursal': (await offline.repo.sucursales())
                .where((s) => s.id == op.sucursalId)
                .firstOrNull
                ?.nombre ??
            'Sucursal',
        'programada_para': op.payload['programada_para'] ?? op.creadoEn,
        'puede_cancelar': true,
        'notas': op.resumen,
        'total_unidades':
            items.fold<int>(0, (s, i) => s + (i['cantidad'] as int? ?? 1)),
        'items': items
            .map((i) => {
                  'cantidad': i['cantidad'],
                  'producto': 'Variante #${i['variante_id']}'
                })
            .toList()
      });
    }
    for (var i = 0; i < resultado.length; i++) {
      final reservaId = resultado[i]['id'];
      final cancelacion = operaciones
          .where((o) =>
              o.tipo == 'CANCELAR_RESERVA' &&
              ['REGISTRADA_LOCAL', 'ENVIADA'].contains(o.estado) &&
              o.payload['reserva_id'] == reservaId)
          .firstOrNull;
      if (cancelacion != null) {
        resultado[i] = {
          ...resultado[i],
          'pendiente_local': true,
          'estado_local': 'Pendiente de enviar · se cancelará al reconectar',
          'puede_cancelar': false
        };
      }
    }
    return resultado;
  }

  Future<String?> _pedirMotivo() {
    final motivo = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Cancelar reserva'),
        content: TextField(
            controller: motivo,
            maxLength: 200,
            decoration: const InputDecoration(labelText: 'Motivo (opcional)')),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx), child: const Text('Volver')),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, motivo.text),
              child: const Text('Cancelar reserva')),
        ],
      ),
    );
  }

  Future<void> _nuevaReserva() async {
    await Navigator.push<bool>(
        context, MaterialPageRoute(builder: (_) => const MiReservaScreen()));
    await _cargar();
  }

  Future<void> _cancelar(Map<String, dynamic> r) async {
    final motivo = await _pedirMotivo();
    if (motivo == null) return; // el cliente se arrepintió
    final offline = context.read<OfflineController>();
    if (r['pendiente_local'] == true) {
      final local = offline.operaciones.where((o) => o.id == r['id']).firstOrNull;
      if (local != null) {
        await offline.deshacer(local); // devuelve también el stock reservado en la copia local
      } else {
        await offline.repo.borrarOperacionLocal(r['id'] as String);
      }
      await offline.recargar();
      await _cargar();
      return;
    }
    if (!offline.enLinea) {
      await offline.registrar(
          tipo: 'CANCELAR_RESERVA',
          payload: {'reserva_id': r['id'], 'motivo': motivo},
          sucursalId: r['sucursal_id'] as int,
          resumen: 'Cancelar reserva ${r['codigo']}');
      await _cargar();
      return;
    }
    try {
      await _repo.cancelar(r['id'] as int, motivo: motivo);
      await _cargar();
    } on ApiException catch (e) {
      if (e.sinConexion) {
        await offline.registrar(
            tipo: 'CANCELAR_RESERVA',
            payload: {'reserva_id': r['id'], 'motivo': motivo},
            sucursalId: r['sucursal_id'] as int,
            resumen: 'Cancelar reserva ${r['codigo']}');
        await _cargar();
      } else if (mounted) {
        setState(() => _error = e.mensaje);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final refresco = context.select<OfflineController, int>((c) => c.refresco);
    if (_refrescoVisto != null && _refrescoVisto != refresco) {
      WidgetsBinding.instance.addPostFrameCallback((_) { if (mounted) _cargar(); }); // tras sincronizar o al volver la red, la lista se actualiza sola
    }
    _refrescoVisto = refresco;
    return Scaffold(
      appBar:
          widget.integrado ? null : AppBar(title: const Text('Mis reservas')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _nuevaReserva,
        icon: const Icon(Icons.bookmark_add_outlined),
        label: Text('Mi reserva (${context.watch<ReservaBorrador>().total})'),
      ),
      body: RefreshIndicator(
        onRefresh: _cargar,
        child: ListView(
            padding: EdgeInsets.fromLTRB(
                16, 16, 16, MediaQuery.viewPaddingOf(context).bottom + 16),
            children: [
              OperacionesConProblema(tipos: const ['RESERVA', 'CANCELAR_RESERVA'], titulo: 'Reservas que no se pudieron realizar', alElegirOtra: (prenda) => Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => CatalogoScreen(consultaInicial: prenda)))),
              if (_error != null)
                Text(_error!, style: const TextStyle(color: Colors.red)),
              if (_reservas == null && _error == null)
                const Center(child: CircularProgressIndicator()),
              if (_reservas != null && _reservas!.isEmpty)
                const Padding(
                    padding: EdgeInsets.all(24),
                    child: Center(child: Text('Todavía no tiene reservas.'))),
              for (final r in _reservas ?? const <Map<String, dynamic>>[])
                Card(
                  child: ListTile(
                    title: Text('${r['codigo']} · ${r['estado']}'),
                    subtitle: Text(
                        '${r['pendiente_local'] == true ? '${r['estado_local']} · ' : ''}${r['sucursal']} · ${fechaCorta(r['programada_para'] as String?)}\n${((r['items'] as List?) ?? const []).map((i) => '${(i as Map)['cantidad']}× ${i['producto']}').join(', ')}'),
                    isThreeLine: true,
                    trailing: r['puede_cancelar'] == true
                        ? TextButton(
                            onPressed: () => _cancelar(r),
                            child: const Text('Cancelar'))
                        : null,
                  ),
                ),
            ]),
      ),
    );
  }
}
