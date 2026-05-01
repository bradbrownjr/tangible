package io.github.bradbrownjr.covet.data.local

import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import io.github.bradbrownjr.covet.data.remote.CollectionDto
import io.github.bradbrownjr.covet.data.remote.ItemDto

class MappersTest {

    private val moshi: Moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()

    @Test
    fun `collection round-trips dto to entity to dto`() {
        val dto = CollectionDto(
            id = "c1",
            name = "Vinyl",
            description = "Records",
            icon = null,
            is_public = false,
            owner_id = "u1",
            default_category_slug = "music",
        )
        val back = dto.toEntity().toDto()
        assertEquals(dto, back)
    }

    @Test
    fun `item round-trips with identifiers`() {
        val dto = ItemDto(
            id = "i1",
            collection_id = "c1",
            category_id = "cat-vinyl",
            category_slug = "music.vinyl",
            title = "Kind of Blue",
            subtitle = "Miles Davis",
            notes = null,
            condition = "VG+",
            quantity = 1,
            purchase_price = 19.99,
            current_value = null,
            currency = "USD",
            location_id = "loc1",
            location_path = listOf("Home", "Office", "Shelf A"),
            identifiers = mapOf("upc" to "074646493427"),
            attrs = mapOf("year" to 1959.0),
        )
        val back = dto.toEntity(moshi).toDto(moshi)
        assertEquals(dto.id, back.id)
        assertEquals(dto.title, back.title)
        assertEquals(dto.category_slug, back.category_slug)
        assertEquals(dto.identifiers["upc"], back.identifiers["upc"])
        assertEquals(dto.purchase_price, back.purchase_price)
        assertEquals(dto.location_id, back.location_id)
        assertEquals(dto.location_path, back.location_path)
        assertNull(back.notes)
    }
}

