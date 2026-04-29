# Standard ProGuard / R8 rules. Most libraries ship their own consumer rules.

# Keep Moshi-generated adapters (codegen) and reflective JSON DTOs.
-keepclassmembers class * {
    @com.squareup.moshi.JsonClass <init>(...);
    @com.squareup.moshi.Json <fields>;
}
-keep @com.squareup.moshi.JsonClass class * { *; }

# Hilt generates components reflectively.
-keep class dagger.hilt.** { *; }
-keep class * extends dagger.hilt.android.internal.managers.ViewComponentManager$FragmentContextWrapper { *; }

# Keep Room entities so reflection in migrations doesn't choke.
-keep class io.github.bradbrownjr.covet.data.local.entity.** { *; }
