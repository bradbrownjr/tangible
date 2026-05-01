package io.github.bradbrownjr.covet.data.local

import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import io.github.bradbrownjr.covet.data.remote.CategoryDto
import io.github.bradbrownjr.covet.data.remote.CollectionDto
import io.github.bradbrownjr.covet.data.remote.ItemDto
import io.github.bradbrownjr.covet.data.remote.LocationDto

/**
 * Conversion between Retrofit DTOs and Room entities.
 * Identifier / attrs maps are stored as JSON text columns.
 */

private val mapType = Types.newParameterizedType(
    Map::class.java,
    String::class.java,
    Any::class.java,
)

private val stringListType =
    Types.newParameterizedType(List::class.java, String::class.java)

private fun Moshi.mapAdapter() = adapter<Map<String, Any?>>(mapType)

private fun Moshi.stringListAdapter() = adapter<List<String>>(stringListType)

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
    val pathAdapter = moshi.stringListAdapter()
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
        locationId = location_id,
        locationPathJson = location_path?.let { pathAdapter.toJson(it) },
        identifiersJson = adapter.toJson(identifiers),
        attrsJson = adapter.toJson(attrs),
        depleted = depleted,
        purchasedAt = purchased_at,
        useByDate = use_by_date,
        dateFrozen = date_frozen,
        dateOpened = date_opened,
        cachedAt = now,
    )
}

fun ItemEntity.toDto(moshi: Moshi): ItemDto {
    val adapter = moshi.mapAdapter()
    val pathAdapter = moshi.stringListAdapter()
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
        location_id = locationId,
        location_path = locationPathJson?.let { pathAdapter.fromJson(it) },
        identifiers = adapter.fromJson(identifiersJson) ?: emptyMap(),
        attrs = adapter.fromJson(attrsJson) ?: emptyMap(),
        depleted = depleted,
        purchased_at = purchasedAt,
        use_by_date = useByDate,
        date_frozen = dateFrozen,
        date_opened = dateOpened,
    )
}

/**
 * Flatten a tree of LocationDto into a list of LocationEntity (drops children).
 * The tree shape is rebuilt in-memory via parent_id when needed.
 */
fun List<LocationDto>.flattenToEntities(now: Long = System.currentTimeMillis()): List<LocationEntity> {
    val out = mutableListOf<LocationEntity>()
    fun walk(node: LocationDto) {
        out.add(
            LocationEntity(
                id = node.id,
                collectionId = node.collection_id,
                parentId = node.parent_id,
                name = node.name,
                kind = node.kind,
                notes = node.notes,
                qrSlug = node.qr_slug,
                itemCount = node.item_count,
                cachedAt = now,
            ),
        )
        node.children.forEach(::walk)
    }
    forEach(::walk)
    return out
}

fun List<LocationEntity>.toTreeDtos(): List<LocationDto> {
    val byParent = groupBy { it.parentId }
    fun build(entity: LocationEntity): LocationDto = LocationDto(
        id = entity.id,
        collection_id = entity.collectionId,
        parent_id = entity.parentId,
        name = entity.name,
        kind = entity.kind,
        notes = entity.notes,
        qr_slug = entity.qrSlug,
        item_count = entity.itemCount,
        children = (byParent[entity.id] ?: emptyList()).map(::build),
    )
    return (byParent[null] ?: emptyList()).map(::build)
}

