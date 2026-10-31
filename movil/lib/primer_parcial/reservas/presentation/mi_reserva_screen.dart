import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../core/network/api_client.dart';
import '../../../features/auth/data/auth_repository.dart';
import '../../../features/offline/presentation/modo_offline_screen.dart' show fechaCorta;
import '../../catalogo/data/catalogo_repository.dart';
import '../data/reserva_borrador.dart';
import '../data/reservas_repository.dart';

/// CU-09 · «Mi reserva»: las prendas elegidas, la sucursal y el día y hora aproximada de la visita. Confirmar crea la reserva (`POST /reservas`).
class MiReservaScreen extends StatefulWidget {
  const MiReservaScreen({super.key});

  @override
  State<MiReservaScreen> createState() => _MiReservaScreenState();
}

class _MiReservaScreenState extends State<MiReservaScreen> {
  late final ReservasRepository _repo = ReservasRepository(context.read<AuthRepository>().api);
  late final CatalogoRepository _catalogo = CatalogoRepository(context.read<AuthRepository>().api);
  final _notas = TextEditingController();
  List<Map<String, dynamic>> _sucursales = [];
  int? _sucursalId;
  late DateTime _cuando = _manana();
  String? _error;
  bool _enviando = false;

  static DateTime _manana() {
    final m = DateTime.now().add(const Duration(days: 1));
    return DateTime(m.year, m.month, m.day, 11);
  }

  @override
  void initState() {
    super.initState();
    _cargarSucursales();
  }

  @override
  void dispose() {
    _notas.dispose();
    super.dispose();
  }

  Future<void> _cargarSucursales() async {
    try {
      final s = await _catalogo.sucursales();
      if (mounted) setState(() { _sucursales = s; _sucursalId = s.isEmpty ? null : s.first['id'] as int; });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.sinConexion ? 'Sin conexión: la reserva necesita Internet.' : e.mensaje);
    }
  }

  Future<void> _elegirFecha() async {
    final ahora = DateTime.now();
    final dia = await showDatePicker(context: context, initialDate: _cuando, firstDate: ahora, lastDate: ahora.add(const Duration(days: 60)));
    if (dia == null || !mounted) return;
    final hora = await showTimePicker(context: context, initialTime: TimeOfDay.fromDateTime(_cuando));
    if (hora == null) return;
    setState(() => _cuando = DateTime(dia.year, dia.month, dia.day, hora.hour, hora.minute));
  }

  Future<void> _confirmar(ReservaBorrador borrador) async {
    if (_sucursalId == null) return;
    setState(() { _enviando = true; _error = null; });
    try {
      final r = await _repo.reservar(borrador.aCuerpo(sucursalId: _sucursalId!, cuando: _cuando, notas: _notas.text));
      borrador.vaciar();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Reserva ${r['codigo']} confirmada. Presente ese código en la tienda.')));
      Navigator.pop(context, true);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.sinConexion ? 'Sin conexión: la reserva necesita Internet.' : e.mensaje);
    }
    if (mounted) setState(() => _enviando = false);
  }

  @override
  Widget build(BuildContext context) {
    final borrador = context.watch<ReservaBorrador>();
    return Scaffold(
      appBar: AppBar(title: const Text('Mi reserva')),
      body: borrador.prendas.isEmpty
          ? const Padding(padding: EdgeInsets.all(24), child: Center(child: Text('Todavía no eligió prendas. En el catálogo use «Agregar a mi reserva».', textAlign: TextAlign.center)))
          : ListView(padding: const EdgeInsets.all(16), children: [
              const Text('Elija la sucursal y el horario aproximado; allí podrá probarse las prendas y decidir cuáles comprar.'),
              const SizedBox(height: 8),
              for (final p in borrador.prendas)
                Card(
                  child: ListTile(
                    title: Text(p.producto),
                    subtitle: Text('${p.talla} · ${p.color} · ${p.sku}'),
                    trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                      IconButton(icon: const Icon(Icons.remove_circle_outline), onPressed: p.cantidad > 1 ? () => borrador.cambiarCantidad(p.varianteId, p.cantidad - 1) : null),
                      Text('${p.cantidad}'),
                      IconButton(icon: const Icon(Icons.add_circle_outline), onPressed: p.cantidad < 10 && p.cantidad < p.max ? () => borrador.cambiarCantidad(p.varianteId, p.cantidad + 1) : null),
                      IconButton(icon: const Icon(Icons.delete_outline), onPressed: () => borrador.quitar(p.varianteId)),
                    ]),
                  ),
                ),
              const SizedBox(height: 8),
              DropdownButtonFormField<int>(
                initialValue: _sucursalId,
                decoration: const InputDecoration(labelText: 'Sucursal'),
                items: [for (final s in _sucursales) DropdownMenuItem<int>(value: s['id'] as int, child: Text('${s['nombre']} · ${s['ciudad']}'))],
                onChanged: (v) => setState(() => _sucursalId = v),
              ),
              const SizedBox(height: 8),
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Día y hora aproximada de su visita'),
                subtitle: Text(fechaCorta(_cuando.toIso8601String())),
                trailing: const Icon(Icons.edit_calendar_outlined),
                onTap: _elegirFecha,
              ),
              TextField(controller: _notas, maxLength: 300, decoration: const InputDecoration(labelText: 'Notas para la tienda (opcional)')),
              if (_error != null) Padding(padding: const EdgeInsets.only(bottom: 8), child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error))),
              Text('${borrador.total} prenda(s) · el stock se aparta de inmediato y la reserva vence 24 horas después del horario elegido.', style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: 12),
              Row(children: [
                OutlinedButton(onPressed: _enviando ? null : borrador.vaciar, child: const Text('Vaciar')),
                const SizedBox(width: 12),
                Expanded(child: FilledButton(onPressed: _enviando || _sucursalId == null ? null : () => _confirmar(borrador), child: Text(_enviando ? 'Reservando…' : 'Confirmar reserva'))),
              ]),
            ]),
    );
  }
}
