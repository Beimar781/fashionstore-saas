import 'package:flutter/material.dart';

import '../data/datos_entrega.dart';

/// CU-11 · Entrega y facturación, antes de pagar. Devuelve los datos con `Navigator.pop`; si el cliente vuelve atrás, devuelve null.
class EntregaScreen extends StatefulWidget {
  const EntregaScreen({super.key, this.sucursal});

  final String? sucursal;

  @override
  State<EntregaScreen> createState() => _EntregaScreenState();
}

class _EntregaScreenState extends State<EntregaScreen> {
  final _direccion = TextEditingController();
  final _nit = TextEditingController();
  final _razon = TextEditingController();
  bool _domicilio = false;
  String? _error;

  @override
  void dispose() {
    _direccion.dispose();
    _nit.dispose();
    _razon.dispose();
    super.dispose();
  }

  void _continuar() {
    final datos = DatosEntrega(domicilio: _domicilio, direccion: _direccion.text, nitCi: _nit.text, razonSocial: _razon.text);
    final error = datos.validar();
    if (error != null) {
      setState(() => _error = error);
      return;
    }
    Navigator.pop(context, datos);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Entrega y facturación')),
        body: ListView(padding: const EdgeInsets.all(16), children: [
          SegmentedButton<bool>(
            segments: [
              ButtonSegment(value: false, icon: const Icon(Icons.store_outlined), label: Text('Retiro en ${widget.sucursal ?? 'la sucursal'}')),
              const ButtonSegment(value: true, icon: Icon(Icons.local_shipping_outlined), label: Text('A domicilio')),
            ],
            selected: {_domicilio},
            onSelectionChanged: (s) => setState(() => _domicilio = s.first),
          ),
          if (_domicilio) ...[
            const SizedBox(height: 12),
            TextField(
              controller: _direccion,
              maxLength: 300,
              decoration: const InputDecoration(labelText: 'Dirección de entrega', hintText: 'Calle, número, barrio y referencia'),
            ),
          ],
          const SizedBox(height: 12),
          TextField(controller: _nit, maxLength: 20, decoration: const InputDecoration(labelText: 'NIT o CI')),
          TextField(controller: _razon, maxLength: 120, decoration: const InputDecoration(labelText: 'Razón social (opcional)')),
          if (_error != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error))),
          const SizedBox(height: 16),
          FilledButton(onPressed: _continuar, child: const Text('Continuar al pago')),
        ]),
      );
}
