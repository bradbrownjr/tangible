package io.github.bradbrownjr.tangible.data.remote

import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import org.junit.Assert.assertEquals
import org.junit.Test

class DtosTest {
    private val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()

    @Test fun `parses login response`() {
        val json = """
            {
              "user": {"id":"01","username":"alice","email":null,"display_name":null,"is_admin":false},
              "expires_at": "2026-05-01T00:00:00Z"
            }
        """.trimIndent()
        val s = moshi.adapter(SessionInfoDto::class.java).fromJson(json)!!
        assertEquals("alice", s.user.username)
    }

    @Test fun `parses item with extras`() {
        val json = """
            {
              "id":"02","collection_id":"01","category_id":"cat-1","title":"Dune",
              "identifiers":{"barcode":"012"},
              "attrs":{"year":2021}
            }
        """.trimIndent()
        val i = moshi.adapter(ItemDto::class.java).fromJson(json)!!
        assertEquals("Dune", i.title)
        assertEquals("cat-1", i.category_id)
        assertEquals("012", i.identifiers["barcode"])
    }
}
