package io.github.bradbrownjr.covet.data.remote

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class LoginRequest(val username: String, val password: String)

@JsonClass(generateAdapter = true)
data class TokenInfo(
    val id: String,
    val name: String,
    val token: String? = null,
    val last_used_at: String? = null,
    val expires_at: String? = null,
    val created_at: String,
)

@JsonClass(generateAdapter = true)
data class UserDto(
    val id: String,
    val username: String,
    val email: String? = null,
    val display_name: String? = null,
    val is_admin: Boolean = false,
)

@JsonClass(generateAdapter = true)
data class SessionInfoDto(val user: UserDto, val expires_at: String)

@JsonClass(generateAdapter = true)
data class CollectionDto(
    val id: String,
    val name: String,
    val description: String? = null,
    val icon: String? = null,
    val is_public: Boolean = false,
    val owner_id: String,
    val default_category_slug: String? = null,
)

@JsonClass(generateAdapter = true)
data class CollectionCreate(
    val name: String,
    val description: String? = null,
    val default_category_slug: String? = null,
)

@JsonClass(generateAdapter = true)
data class CategoryDto(
    val id: String,
    val parent_id: String? = null,
    val slug: String,
    val name: String,
    val description: String? = null,
    val position: Int = 0,
)

@JsonClass(generateAdapter = true)
data class ScrapeResponse(
    val title: String? = null,
    val description: String? = null,
    val category: String? = null,
)

@JsonClass(generateAdapter = true)
data class ScrapeRequest(val url: String)

@JsonClass(generateAdapter = true)
data class BarcodeLookupRequest(val barcode: String)

@JsonClass(generateAdapter = true)
data class BarcodeCandidateDto(
    val provider: String,
    val url: String,
    val title: String? = null,
    val description: String? = null,
    val image_url: String? = null,
    val category: String? = null,
    val attrs: Map<String, @JvmSuppressWildcards Any?> = emptyMap(),
)

@JsonClass(generateAdapter = true)
data class BarcodeLookupResponse(val candidates: List<BarcodeCandidateDto>)

@JsonClass(generateAdapter = true)
data class ItemDto(
    val id: String,
    val collection_id: String,
    val category_id: String,
    val category_slug: String? = null,
    val title: String,
    val subtitle: String? = null,
    val notes: String? = null,
    val condition: String? = null,
    val quantity: Int = 1,
    val purchase_price: Double? = null,
    val current_value: Double? = null,
    val currency: String? = null,
    val location: String? = null,
    val identifiers: Map<String, Any?> = emptyMap(),
    val attrs: Map<String, Any?> = emptyMap(),
)

@JsonClass(generateAdapter = true)
data class ItemCreate(
    val collection_id: String,
    val category: String,       // leaf slug, e.g. "music.vinyl"
    val title: String,
    val subtitle: String? = null,
    val notes: String? = null,
    val identifiers: Map<String, String> = emptyMap(),
)
