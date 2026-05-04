package io.github.bradbrownjr.tangible.data.repo

import com.squareup.moshi.Moshi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import io.github.bradbrownjr.tangible.data.local.CategoryDao
import io.github.bradbrownjr.tangible.data.local.CollectionDao
import io.github.bradbrownjr.tangible.data.local.ItemDao
import io.github.bradbrownjr.tangible.data.local.LocationDao
import io.github.bradbrownjr.tangible.data.local.flattenToEntities
import io.github.bradbrownjr.tangible.data.local.toDto
import io.github.bradbrownjr.tangible.data.local.toEntity
import io.github.bradbrownjr.tangible.data.local.toTreeDtos
import io.github.bradbrownjr.tangible.data.remote.CategoryDto
import io.github.bradbrownjr.tangible.data.remote.ContactDto
import io.github.bradbrownjr.tangible.data.remote.CollectionCreate
import io.github.bradbrownjr.tangible.data.remote.CollectionDto
import io.github.bradbrownjr.tangible.data.remote.TangibleApi
import io.github.bradbrownjr.tangible.data.remote.ItemCreate
import io.github.bradbrownjr.tangible.data.remote.ItemBulkArchiveRequest
import io.github.bradbrownjr.tangible.data.remote.ItemBulkDeleteRequest
import io.github.bradbrownjr.tangible.data.remote.ItemBulkLendRequest
import io.github.bradbrownjr.tangible.data.remote.ItemBulkPatchRequest
import io.github.bradbrownjr.tangible.data.remote.ItemBulkRestoreRequest
import io.github.bradbrownjr.tangible.data.remote.ItemBulkTagRequest
import io.github.bradbrownjr.tangible.data.remote.ItemDto
import io.github.bradbrownjr.tangible.data.remote.ItemPatch
import io.github.bradbrownjr.tangible.data.remote.LocationCreate
import io.github.bradbrownjr.tangible.data.remote.LocationDto
import io.github.bradbrownjr.tangible.data.remote.LocationPatch
import io.github.bradbrownjr.tangible.data.remote.ManualBundleDto
import io.github.bradbrownjr.tangible.data.remote.PhotoDto
import io.github.bradbrownjr.tangible.data.remote.RestockRequest
import io.github.bradbrownjr.tangible.data.remote.TagDto
import io.github.bradbrownjr.tangible.data.remote.ShoppingFeedEntryDto
import io.github.bradbrownjr.tangible.data.remote.ShoppingItemCreateRequest
import io.github.bradbrownjr.tangible.data.remote.ShoppingItemReadDto
import io.github.bradbrownjr.tangible.data.remote.ShoppingStoreDto
import io.github.bradbrownjr.tangible.data.remote.ShoppingAisleDto
import io.github.bradbrownjr.tangible.data.remote.ShoppingStoreCreate
import io.github.bradbrownjr.tangible.data.remote.ShoppingStorePatch
import io.github.bradbrownjr.tangible.data.remote.ShoppingAisleCreate
import io.github.bradbrownjr.tangible.data.remote.ShoppingAislePatch
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Offline-first collection repository.
 */
@Singleton
class CollectionRepository @Inject constructor(
    private val api: TangibleApi,
    private val dao: CollectionDao,
) {
    fun observe(): Flow<List<CollectionDto>> =
        dao.observeAll().map { rows -> rows.map { it.toDto() } }

    fun observeOne(id: String): Flow<CollectionDto?> =
        dao.observe(id).map { it?.toDto() }

    suspend fun list(): List<CollectionDto> {
        val remote = api.listCollections()
        dao.upsertAll(remote.map { it.toEntity() })
        dao.deleteMissing(remote.map { it.id })
        return remote
    }

    suspend fun get(id: String): CollectionDto {
        val cached = dao.get(id)
        return try {
            val fresh = api.getCollection(id)
            dao.upsertAll(listOf(fresh.toEntity()))
            fresh
        } catch (t: Throwable) {
            cached?.toDto() ?: throw t
        }
    }

    suspend fun create(
        name: String,
        description: String? = null,
        defaultCategorySlug: String? = null,
    ): CollectionDto {
        val created = api.createCollection(
            CollectionCreate(
                name = name,
                description = description,
                default_category_slug = defaultCategorySlug,
            )
        )
        dao.upsertAll(listOf(created.toEntity()))
        return created
    }

    suspend fun update(id: String, patch: io.github.bradbrownjr.tangible.data.remote.CollectionPatch): CollectionDto {
        val updated = api.patchCollection(id, patch)
        dao.upsertAll(listOf(updated.toEntity()))
        return updated
    }

    suspend fun delete(id: String) {
        api.deleteCollection(id)
        dao.deleteById(id)
    }
}

@Singleton
class CategoryRepository @Inject constructor(
    private val api: TangibleApi,
    private val dao: CategoryDao,
) {
    fun observe(): Flow<List<CategoryDto>> =
        dao.observeAll().map { rows -> rows.map { it.toDto() } }

    suspend fun load(): List<CategoryDto> {
        return try {
            val remote = api.listCategories()
            dao.upsertAll(remote.map { it.toEntity() })
            remote
        } catch (t: Throwable) {
            // Fall back to cached values if offline.
            dao.getAll().map { it.toDto() }.ifEmpty { throw t }
        }
    }
}

@Singleton
class ItemRepository @Inject constructor(
    private val api: TangibleApi,
    private val dao: ItemDao,
    private val moshi: Moshi,
) {
    suspend fun listTags(): List<TagDto> = api.listTags()

    suspend fun listContacts(): List<ContactDto> = api.listContacts()

    fun observe(collectionId: String): Flow<List<ItemDto>> =
        dao.observeForCollection(collectionId).map { rows -> rows.map { it.toDto(moshi) } }

    suspend fun list(
        collectionId: String,
        search: String? = null,
        categorySubtree: String? = null,
    ): List<ItemDto> {
        val remote = api.listItems(
            collectionId = collectionId,
            search = search?.takeIf { it.isNotBlank() },
            categorySubtree = categorySubtree,
        )
        // Only mirror unfiltered results into the cache so filters don't
        // delete entries that simply didn't match the current query.
        if (search.isNullOrBlank() && categorySubtree == null) {
            dao.upsertAll(remote.map { it.toEntity(moshi) })
            dao.deleteMissingIn(collectionId, remote.map { it.id })
        }
        return remote
    }

    suspend fun create(
        collectionId: String,
        categorySlug: String,
        title: String,
        identifiers: Map<String, String> = emptyMap(),
    ): ItemDto {
        val created = api.createItem(
            ItemCreate(
                collection_id = collectionId,
                category = categorySlug,
                title = title,
                identifiers = identifiers,
            ),
        )
        dao.upsertAll(listOf(created.toEntity(moshi)))
        return created
    }

    suspend fun get(id: String): ItemDto {
        val fresh = api.getItem(id)
        dao.upsertAll(listOf(fresh.toEntity(moshi)))
        return fresh
    }

    suspend fun update(id: String, patch: io.github.bradbrownjr.tangible.data.remote.ItemPatch): ItemDto {
        val updated = api.patchItem(id, patch)
        dao.upsertAll(listOf(updated.toEntity(moshi)))
        return updated
    }

    suspend fun update(id: String, depleted: Boolean? = null): ItemDto {
        val patch = ItemPatch(depleted = depleted)
        return update(id, patch)
    }

    suspend fun shoppingList(): List<ItemDto> {
        return api.getShoppingList()
    }

    suspend fun restock(itemId: String, quantity: Int = 1, useByDate: String? = null) {
        api.restockItem(
            itemId,
            RestockRequest(
                quantity = quantity,
                purchased_at = java.time.OffsetDateTime.now().toString(),
                use_by_date = useByDate,
                mark_in_stock = true,
            ),
        )
    }

    suspend fun delete(id: String) {
        api.deleteItem(id)
        dao.delete(id)
    }

    suspend fun bulkPatch(
        collectionId: String,
        itemIds: List<String>,
        depleted: Boolean? = null,
        wanted: Boolean? = null,
        locationId: String? = null,
    ) {
        if (itemIds.isEmpty()) return
        api.bulkPatchItems(
            ItemBulkPatchRequest(
                collection_id = collectionId,
                item_ids = itemIds,
                depleted = depleted,
                wanted = wanted,
                location_id = locationId,
            ),
        )
    }

    suspend fun bulkMoveLocation(collectionId: String, itemIds: List<String>, locationId: String?) {
        if (itemIds.isEmpty()) return
        api.bulkPatchItems(
            ItemBulkPatchRequest(
                collection_id = collectionId,
                item_ids = itemIds,
                location_id = locationId,
            ),
        )
    }

    suspend fun bulkArchive(collectionId: String, itemIds: List<String>) {
        if (itemIds.isEmpty()) return
        api.bulkArchiveItems(
            ItemBulkArchiveRequest(collection_id = collectionId, item_ids = itemIds),
        )
    }

    suspend fun bulkRestore(collectionId: String, itemIds: List<String>) {
        if (itemIds.isEmpty()) return
        api.bulkRestoreItems(
            ItemBulkRestoreRequest(collection_id = collectionId, item_ids = itemIds),
        )
    }

    suspend fun bulkDelete(collectionId: String, itemIds: List<String>) {
        if (itemIds.isEmpty()) return
        api.bulkDeleteItems(
            ItemBulkDeleteRequest(collection_id = collectionId, item_ids = itemIds),
        )
    }

    suspend fun bulkTag(collectionId: String, itemIds: List<String>, tagId: String, mode: String) {
        if (itemIds.isEmpty()) return
        api.bulkTagItems(
            ItemBulkTagRequest(
                collection_id = collectionId,
                item_ids = itemIds,
                tag_ids = listOf(tagId),
                mode = mode,
            ),
        )
    }

    suspend fun bulkLend(collectionId: String, itemIds: List<String>, contactId: String) {
        if (itemIds.isEmpty()) return
        api.bulkLendItems(
            ItemBulkLendRequest(
                collection_id = collectionId,
                item_ids = itemIds,
                contact_id = contactId,
            ),
        )
    }
}

@Singleton
class PhotoRepository @Inject constructor(
    private val api: TangibleApi,
) {
    suspend fun list(itemId: String): List<PhotoDto> = api.listPhotos(itemId)

    suspend fun delete(photoId: String) = api.deletePhoto(photoId)

    suspend fun upload(itemId: String, bytes: ByteArray, mimeType: String): List<PhotoDto> {
        val body = bytes.toRequestBody(mimeType.toMediaType())
        val part = MultipartBody.Part.createFormData("files", "photo.jpg", body)
        return api.uploadPhotos(itemId, part)
    }
}

@Singleton
class LocationRepository @Inject constructor(
    private val api: TangibleApi,
    private val dao: LocationDao,
) {
    fun observeTree(collectionId: String): Flow<List<LocationDto>> =
        dao.observeForCollection(collectionId).map { rows -> rows.toTreeDtos() }

    suspend fun listTree(collectionId: String): List<LocationDto> {
        val remote = api.listLocations(collectionId)
        val flat = remote.flattenToEntities()
        dao.upsertAll(flat)
        dao.deleteMissingIn(collectionId, flat.map { it.id })
        return remote
    }

    suspend fun create(
        collectionId: String,
        name: String,
        kind: String = "container",
        parentId: String? = null,
        notes: String? = null,
    ): LocationDto {
        val created = api.createLocation(
            LocationCreate(
                collection_id = collectionId,
                name = name,
                kind = kind,
                parent_id = parentId,
                notes = notes,
            ),
        )
        listTree(collectionId)
        return created
    }

    suspend fun update(
        id: String,
        collectionId: String,
        name: String? = null,
        kind: String? = null,
        parentId: String? = null,
        notes: String? = null,
    ): LocationDto {
        val updated = api.patchLocation(
            id,
            LocationPatch(name = name, kind = kind, parent_id = parentId, notes = notes),
        )
        listTree(collectionId)
        return updated
    }

    suspend fun delete(id: String, collectionId: String) {
        api.deleteLocation(id)
        dao.delete(id)
        listTree(collectionId)
    }
}

@Singleton
class BundleRepository @Inject constructor(
    private val api: TangibleApi,
) {
    suspend fun listForCollection(collectionId: String): List<ManualBundleDto> =
        api.listBundles(collectionId)

    suspend fun listForItem(itemId: String): List<ManualBundleDto> =
        api.listItemBundles(itemId)

    suspend fun get(bundleId: String): ManualBundleDto =
        api.getBundle(bundleId)
}

@Singleton
class ShoppingRepository @Inject constructor(
    private val api: TangibleApi,
) {
    suspend fun feed(listType: String? = null): List<ShoppingFeedEntryDto> = api.getShoppingFeed(listType)

    suspend fun addItem(
        collectionId: String,
        name: String,
        quantity: Int = 1,
        unit: String? = null,
        notes: String? = null,
        categorySlug: String? = null,
        listType: String = "groceries",
    ): ShoppingItemReadDto = api.createShoppingItem(
        ShoppingItemCreateRequest(
            collection_id = collectionId,
            name = name,
            quantity = quantity,
            unit = unit,
            notes = notes,
            category_slug = categorySlug,
            list_type = listType,
        )
    )

    suspend fun deleteItem(id: String) = api.deleteShoppingItem(id)

    suspend fun purchaseItem(id: String) = api.purchaseShoppingItem(id)

    // Stores
    suspend fun listStores(): List<ShoppingStoreDto> = api.listShoppingStores()

    suspend fun createStore(name: String): ShoppingStoreDto =
        api.createShoppingStore(ShoppingStoreCreate(name))

    suspend fun updateStore(id: String, name: String): ShoppingStoreDto =
        api.updateShoppingStore(id, ShoppingStorePatch(name))

    suspend fun deleteStore(id: String) = api.deleteShoppingStore(id)

    // Aisles
    suspend fun listAisles(storeId: String): List<ShoppingAisleDto> =
        api.listShoppingAisles(storeId)

    suspend fun createAisle(
        storeId: String,
        name: String,
        position: Int = 0,
        categorySlugs: List<String> = emptyList(),
    ): ShoppingAisleDto = api.createShoppingAisle(
        storeId,
        ShoppingAisleCreate(name = name, position = position, category_slugs = categorySlugs),
    )

    suspend fun updateAisle(
        storeId: String,
        aisleId: String,
        name: String? = null,
        position: Int? = null,
        categorySlugs: List<String>? = null,
    ): ShoppingAisleDto = api.updateShoppingAisle(
        storeId,
        aisleId,
        ShoppingAislePatch(name = name, position = position, category_slugs = categorySlugs),
    )

    suspend fun deleteAisle(storeId: String, aisleId: String) =
        api.deleteShoppingAisle(storeId, aisleId)

    suspend fun reorderAisles(storeId: String, aisleIds: List<String>) =
        api.reorderShoppingAisles(storeId, aisleIds)
}
