import 'package:flutter/widgets.dart';

/// Mantiene todas las rutas por encima del área reservada para la navegación del sistema.
class AreaSeguraAplicacion extends StatelessWidget {
  const AreaSeguraAplicacion({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) =>
      SafeArea(top: false, bottom: true, child: child);
}
