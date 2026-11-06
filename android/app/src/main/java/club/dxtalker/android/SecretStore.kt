package club.dxtalker.android
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import javax.crypto.KeyGenerator
import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import java.util.Base64
object SecretStore {
    private fun key():SecretKey {
        val store=KeyStore.getInstance("AndroidKeyStore").apply{load(null)}
        (store.getKey("DXTalkerCredentials",null) as? SecretKey)?.let{return it}
        val generator=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore")
        generator.init(KeyGenParameterSpec.Builder("DXTalkerCredentials",KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
        return generator.generateKey()
    }
    fun protect(text:String):String {
        if(text.isEmpty())return ""
        val cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.ENCRYPT_MODE,key())
        return "ks1:"+Base64.getEncoder().encodeToString(cipher.iv+cipher.doFinal(text.toByteArray(Charsets.UTF_8)))
    }
    fun reveal(text:String):String {
        if(!text.startsWith("ks1:"))return text // Read legacy values for migration only.
        val raw=Base64.getDecoder().decode(text.substring(4));require(raw.size>=28)
        val cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.DECRYPT_MODE,key(),GCMParameterSpec(128,raw.copyOfRange(0,12)))
        return String(cipher.doFinal(raw.copyOfRange(12,raw.size)),Charsets.UTF_8)
    }
}
