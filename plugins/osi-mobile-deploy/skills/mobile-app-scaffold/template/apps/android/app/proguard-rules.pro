# Add project-specific ProGuard rules here.

# Keep all data model classes (Kotlin data classes used for JSON parsing).
-keep class com.example.myapp.model.** { *; }

# Kotlin serialization
-keepattributes InnerClasses
-dontnote kotlinx.serialization.SerializationKt
-keep,includedescriptorclasses class com.example.myapp.**$$serializer { *; }
