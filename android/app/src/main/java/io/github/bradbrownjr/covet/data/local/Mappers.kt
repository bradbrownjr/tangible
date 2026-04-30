package io.github.bradbrownjr.covet.data.local

import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import io.github.bradbrownjr.covet.data.remote.CategoryDto
import io.github.bradbrownjr.covet.data.remote.CollectionDto
import io.github.bradbrownjr.covet.data.remote.ItemDto

/**
 * Conversion between Retrofit DTOs and Room entities.
 * Identifier / attrs maps are stored as JSON text columns.
 */

private val mapType = Types.newParameterizedType(
    Map::class.java,
    String::class.java,
    Any::class.java,
)

private fun Moshi.mapAdapter() = adapter<Map<String, Any?>>(mapType)

fun CollectionDto.toEntity(now: Long = System.currentTimeMillis()): CollectionEntity =
    CollectionEntity(
        id = id,
        name = name,
        description = description,
        icon = icon,
        isPublic = is_public,
        ownerId = owner_id,
        defaultCategorySlug = default_category_slug,
        cachedAt = now,
    )

fun CollectionEntity.toDto(): CollectionDto =
    CollectionDto(
        id = id,
        name = name,
        description = description,
        icon = icon,
        is_public = isPublic,
        owner_id = ownerId,
        default_category_slug = defaultCategorySlug,
    )

fun CategoryDto.toEntity(now: Long = System.currentTimeMillis()): CategoryEntity =
    CategoryEntity(
        id = id,
        parentId = parent_id,
        slug = slug,
        name = name,
        description = description,
        position = position,
        cachedAt = now,
    )

fun CategoryEntity.toDto(): CategoryDto =
    CategoryDto(
        id = id,
        parent_id = parentId,
        slug = slug,
        name = name,
        description = description,
        position = position,
    )

fun ItemDto.toEntity(moshi: Moshi, now: Long = System.currentTimeMillis()): ItemEntity {
    val adapter = moshi.mapAdapter()
    return ItemEntity(
        id = id,
        collectionId = collection_id,
        categoryId = category_id,
        categorySlug = category_slug,
        title = title,
        subtitle = subtitle,
        notes = notes,
        condition = condition,
        quantity = quantity,
        purchasePrice = purchase_price,
        currentValue = current_value,
        currency = currency,
        location = location,
        identifiersJson = adapter.toJson(identifiers),
        attrsJson = adapter.toJson(attrs),
        depleted = depleted,
        cachedAt = now,
    )
}

fun ItemEntity.toDto(moshi: Moshi): ItemDto {
    val adapter = moshi.mapAdapter()
    return ItemDto(
        id = id,
        collection_id = collectionId,
        category_id = categoryId,
        category_slug = categorySlug,
        title = title,
        subtitle = subtitle,
        notes = notes,
        condition = condition,
        quantity = quantity,
        purchase_price = purchasePrice,
        current_value = currentValue,
        currency = currency,
        location = location,
        identifiers = adapter.fromJson(identifiersJson) ?: emptyMap(),
        attrs = adapter.fromJson(attrsJson) ?: emptyMap(),
        depleted = depleted,
    )
}

