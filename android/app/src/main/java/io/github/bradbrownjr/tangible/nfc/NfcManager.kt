package io.github.bradbrownjr.tangible.nfc

import android.content.Intent
import android.nfc.NdefMessage
import android.nfc.NdefRecord
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.nfc.tech.Ndef
import android.nfc.tech.NdefFormatable
import android.os.Build
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

/**
 * Singleton that manages NFC tag reading and writing for Tangible item tags.
 *
 * Tag format: a URI NDEF record containing `tangible://item/<item-id>`.
 *
 * Usage:
 * - To write: set [pendingWriteItemId] then enable foreground dispatch.
 *   The next TAG_DISCOVERED will write the NDEF record and emit to [writeResult].
 * - To read: handle ACTION_NDEF_DISCOVERED intent; extracted item IDs are
 *   emitted to [pendingNavigationItemId].
 */
object NfcManager {

    private const val TANGIBLE_SCHEME = "tangible"
    private const val TANGIBLE_HOST = "item"

    private val scope = CoroutineScope(Dispatchers.IO)

    /** Non-null when the app is waiting to write a tag. */
    @Volatile
    var pendingWriteItemId: String? = null

    sealed class WriteResult {
        data object Success : WriteResult()
        data class Failure(val message: String) : WriteResult()
    }

    /** Emits results after a write attempt. */
    val writeResult = MutableSharedFlow<WriteResult>(extraBufferCapacity = 1)

    /**
     * Item IDs read from a tapped Tangible NFC tag. The nav layer should
     * collect this and navigate to the item, then reset to null.
     */
    val pendingNavigationItemId = MutableStateFlow<String?>(null)

    /**
     * Call from [MainActivity.onNewIntent] and [MainActivity.onCreate] to
     * handle any NFC-related intent. Returns true if handled.
     */
    fun handleIntent(intent: Intent): Boolean {
        val action = intent.action ?: return false
        val isTagAction = action in setOf(
            NfcAdapter.ACTION_NDEF_DISCOVERED,
            NfcAdapter.ACTION_TECH_DISCOVERED,
            NfcAdapter.ACTION_TAG_DISCOVERED,
        )
        if (!isTagAction) return false

        val tag: Tag? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            intent.getParcelableExtra(NfcAdapter.EXTRA_TAG, Tag::class.java)
        } else {
            @Suppress("DEPRECATION")
            intent.getParcelableExtra(NfcAdapter.EXTRA_TAG)
        }

        val writeTarget = pendingWriteItemId
        if (tag != null && writeTarget != null) {
            // Write mode: write the NDEF record to the tag asynchronously.
            scope.launch { writeNdef(tag, writeTarget) }
            return true
        }

        // Read mode: extract item ID from the NDEF payload.
        if (action == NfcAdapter.ACTION_NDEF_DISCOVERED) {
            return readNdef(intent)
        }

        return false
    }

    private fun writeNdef(tag: Tag, itemId: String) {
        try {
            val record = NdefRecord.createUri("$TANGIBLE_SCHEME://$TANGIBLE_HOST/$itemId")
            val message = NdefMessage(arrayOf(record))

            val ndef = Ndef.get(tag)
            if (ndef != null) {
                ndef.connect()
                try {
                    ndef.writeNdefMessage(message)
                } finally {
                    ndef.close()
                }
                pendingWriteItemId = null
                writeResult.tryEmit(WriteResult.Success)
                return
            }

            val formatable = NdefFormatable.get(tag)
            if (formatable != null) {
                formatable.connect()
                try {
                    formatable.format(message)
                } finally {
                    formatable.close()
                }
                pendingWriteItemId = null
                writeResult.tryEmit(WriteResult.Success)
                return
            }

            writeResult.tryEmit(WriteResult.Failure("Tag does not support NDEF"))
        } catch (e: Exception) {
            writeResult.tryEmit(WriteResult.Failure(e.message ?: "Write failed"))
        }
    }

    private fun readNdef(intent: Intent): Boolean {
        val rawMessages: Array<out android.os.Parcelable>? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            intent.getParcelableArrayExtra(NfcAdapter.EXTRA_NDEF_MESSAGES, NdefMessage::class.java)
        } else {
            @Suppress("DEPRECATION")
            intent.getParcelableArrayExtra(NfcAdapter.EXTRA_NDEF_MESSAGES)
        }
        val first = rawMessages?.firstOrNull() as? NdefMessage ?: return false
        for (record in first.records) {
            val uri = record.toUri() ?: continue
            if (uri.scheme == TANGIBLE_SCHEME && uri.host == TANGIBLE_HOST) {
                val itemId = uri.pathSegments.firstOrNull() ?: continue
                pendingNavigationItemId.value = itemId
                return true
            }
        }
        return false
    }
}
