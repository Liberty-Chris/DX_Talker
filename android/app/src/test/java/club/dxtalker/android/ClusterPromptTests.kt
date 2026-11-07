package club.dxtalker.android
import org.junit.Test
import org.junit.Assert.*

class ClusterPromptTests {
    @Test fun acceptsRealPromptsWithoutInterpretingSpotTextAsAuthentication() {
        for(text in listOf("login:","Enter callsign:","Call sign >","Username: ")) assertTrue(text,ClusterPrompts.login(text))
        assertTrue(ClusterPrompts.password("Password: "))
        for(text in listOf("DX de N0CALL:","DX de N0CALL: 14074 WB4IUY password:","N0CALL:")) {
            assertFalse(text,ClusterPrompts.login(text));assertFalse(text,ClusterPrompts.password(text))
        }
    }
}
