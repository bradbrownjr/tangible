package io.github.bradbrownjr.covet.data.repo

import com.squareup.moshi.Moshi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import io.github.bradbrownjr.covet.data.local.CategoryDao
import io.github.bradbrownjr.covet.data.local.CollectionDao
import io.github.bradbrownjr.covet.data.local.ItemDao
import io.github.bradbrownjr.covet.data.local.toDto
import io.github.bradbrownjr.covet.data.local.toEntity
import io.github.bradbrownjr.covet.data.remote.CategoryDto
import io.github.bradbrownjr.covet.data.remote.CollectionCreate
import io.github.bradbrownjr.covet.data.remote.CollectionDto
import io.github.bradbrownjr.covet.data.remote.CovetApi
import io.github.bradbrownjr.covet.data.remote.ItemCreate
import io.github.bradbrownjr.covet.data.remote.ItemDto
import io.github.bradbrownjr.covet.data.remote.ItemPatch
import io.github.bradbrownjr.covet.data.remote.PhotoDto
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
    private val api: CovetApi,
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

    suspend fun delete(id: String) {
        api.deleteCollection(id)
        dao.deleteById(id)
    }
}

@Singleton
class CategoryRepository @Inject constructor(
    private val api: CovetApi,
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
    private val api: CovetApi,
    private val dao: ItemDao,
    private val moshi: Moshi,
) {
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

    suspend fun update(id: String, patch: io.github.bradbrownjr.covet.data.remote.ItemPatch): ItemDto {
        val updated = api.patchItem(id, patch)
        dao.upsertAll(listOf(updated.toEntity(moshi)))
        return updated
    }

    suspend fun delete(id: String) {
        api.deleteItem(id)
        dao.delete(id)
    }
}

@Singleton
class PhotoRepository @Inject constructor(
    private val api: CovetApi,
) {
    suspend fun list(itemId: String): List<PhotoDto> = api.listPhotos(itemId)

    suspend fun delete(photoId: String) = api.deletePhoto(photoId)

    suspend fun upload(itemId: String, bytes: ByteArray, mimeType: String): List<PhotoDto> {
        val body = bytes.toRequestBody(mimeType.toMediaType())
        val part = MultipartBody.Part.createFormData("files", "photo.jpg", body)
        return api.uploadPhotos(itemId, part)
    }
}
