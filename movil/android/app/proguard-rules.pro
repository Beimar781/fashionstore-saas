# Reglas de respaldo: solo se usan si se activa R8 (isMinifyEnabled = true). Hoy el release se compila sin reducción de código.
# WorkManager (lo traen Firebase, ML Kit y las notificaciones) arranca con androidx.startup y crea su base de datos con Room.
-keep class androidx.work.** { *; }
-keep class * extends androidx.room.RoomDatabase
-keep class androidx.startup.** { *; }
# Stripe
-keep class com.stripe.** { *; }
-keep class com.reactnativestripesdk.** { *; }
-dontwarn com.stripe.android.pushProvisioning.**
-dontwarn com.reactnativestripesdk.pushprovisioning.**
