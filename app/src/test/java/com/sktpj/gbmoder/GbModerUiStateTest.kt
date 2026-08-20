package com.sktpj.gbmoder

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.assertEquals
import org.junit.Test

class GbModerUiStateTest {
    @Test
    fun initialStateMatchesSpecification() {
        val state = GbModerUiState()
        assertEquals("停止中", state.status)
        assertFalse(state.running)
        assertFalse(state.accessibilityReady)
    }

    @Test
    fun javaBridgeUpdatesAreObservable() {
        val state = GbModerUiState()
        state.setStatus("MediaProjection高速キャプチャで開始しました")
        state.setRunning(true)
        state.setAccessibilityReady(true)

        assertEquals("MediaProjection高速キャプチャで開始しました", state.status)
        assertTrue(state.running)
        assertTrue(state.accessibilityReady)
    }
}
