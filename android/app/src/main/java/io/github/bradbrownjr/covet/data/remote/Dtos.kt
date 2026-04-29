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
)

@JsonClass(generateAdapter = true)
data class CollectionCreate(val name: String, val description: String? = null)

@JsonClass(generateAdapter = true)
data class ItemDto(
    val id: String,
    val collection_id: String,
    val type: String,
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
    val type: String,
    val title: String,
    val subtitle: String? = null,
    val notes: String? = null,
    val identifiers: Map<String, String> = emptyMap(),
)
