package club.dxtalker.android

import android.app.*
import android.content.Intent
import android.os.IBinder
import android.speech.tts.TextToSpeech
import java.net.InetSocketAddress
import java.net.Socket
import java.util.Locale
import kotlin.concurrent.thread

class ListenerService : Service(), TextToSpeech.OnInitListener {
    companion object {
        const val UPDATE = "club.dxtalker.android.UPDATE"
        @Volatile var status = "Stopped"
        @Volatile var muted = false
        @Volatile var paused = false
        @Volatile var speechReady = false
        val spots = mutableListOf<String>()
        private val spotPattern = Regex("^DX de\\s+\\S+:\\s+(\\d+(?:\\.\\d+)?)\\s+(\\S+)", RegexOption.IGNORE_CASE)
        fun formatSpot(line: String, template: String): String? {
            val match = spotPattern.find(line) ?: return null
            val frequency = match.groupValues[1]
            val call = match.groupValues[2]
            return template.replace("{call}", call, ignoreCase = true)
                .replace("{frequency}", frequency, ignoreCase = true)
                .replace("{unit}", "kHz", ignoreCase = true)
        }
    }
    private var tts: TextToSpeech? = null
    @Volatile private var running = false
    @Volatile private var socket: Socket? = null
    override fun onBind(intent: Intent?): IBinder? = null
    override fun onCreate() {
        super.onCreate()
        tts = TextToSpeech(this, this)
        val channel = NotificationChannel("dx", "DX cluster listening", NotificationManager.IMPORTANCE_LOW)
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }
    private fun update(message: String? = null) {
        if (message != null) status = message
        sendBroadcast(Intent(UPDATE).setPackage(packageName))
        val manager = getSystemService(NotificationManager::class.java)
        val pending = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        val notification = Notification.Builder(this, "dx")
            .setSmallIcon(android.R.drawable.ic_media_play)
            .setContentTitle("DX Talker")
            .setContentText(status + if (muted) " · Muted" else if (paused) " · Paused" else "")
            .setContentIntent(pending)
            .addAction(android.R.drawable.ic_lock_silent_mode, if (muted) "Unmute" else "Mute", actionIntent("mute", 1))
            .addAction(android.R.drawable.ic_media_pause, if (paused) "Resume" else "Pause", actionIntent("pause", 2))
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Stop", actionIntent("stop", 3))
            .build()
        manager.notify(1, notification)
    }
    private fun actionIntent(action: String, request: Int): PendingIntent =
        PendingIntent.getService(this, request, Intent(this, ListenerService::class.java).setAction(action),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)

    override fun onInit(result: Int) {
        speechReady = result == TextToSpeech.SUCCESS &&
            tts?.setLanguage(Locale.US) != TextToSpeech.LANG_MISSING_DATA &&
            tts?.isLanguageAvailable(Locale.US) != TextToSpeech.LANG_NOT_SUPPORTED
        sendBroadcast(Intent(UPDATE).setPackage(packageName))
    }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            "start" -> {
                if (!running) {
                    running = true
                    val pending = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
                    startForeground(1, Notification.Builder(this, "dx").setSmallIcon(android.R.drawable.ic_media_play)
                        .setContentTitle("DX Talker").setContentText("Connecting").setContentIntent(pending).build())
                    update("Connecting")
                    thread(name = "dx-listener") { listenLoop() }
                }
            }
            "mute" -> { muted = !muted; if (muted) tts?.stop(); update() }
            "pause" -> { paused = !paused; if (paused) tts?.stop(); update() }
            "test" -> speak("New DX. Kilo Foxtrot Four Delta Bravo X ray. Fourteen thousand two hundred kilohertz.", true)
            "stop" -> { running = false; socket?.close(); tts?.stop(); status = "Stopped"; stopForeground(STOP_FOREGROUND_REMOVE); stopSelf() }
        }
        return START_NOT_STICKY
    }
    private fun speak(text: String, force: Boolean = false) {
        if (speechReady && (force || (!muted && !paused))) {
            tts?.speak(text, TextToSpeech.QUEUE_ADD, null, "dx" + System.nanoTime())
        }
    }
    private fun listenLoop() {
        while (running) {
            val prefs = getSharedPreferences("dx", MODE_PRIVATE)
            val host = prefs.getString("host", "")?.trim().orEmpty()
            val port = prefs.getString("port", "7373")?.toIntOrNull()
            if (host.isBlank() || port == null || port !in 1..65535) {
                update("Enter a valid cluster host and port")
                running = false
                break
            }
            try {
                val connection = Socket()
                socket = connection
                connection.connect(InetSocketAddress(host, port), 10000)
                connection.soTimeout = 1000
                update("Connected to $host:$port")
                val input = connection.getInputStream()
                val output = connection.getOutputStream()
                val buffer = ByteArray(4096)
                val line = StringBuilder()
                val prompt = StringBuilder()
                var loginSent = false
                var passwordSent = false
                var lastPrompt = ""
                while (running && !connection.isClosed) {
                    val count = try { input.read(buffer) } catch (_: java.net.SocketTimeoutException) { continue }
                    if (count < 0) break
                    var index = 0
                    while (index < count) {
                        val byte = buffer[index].toInt() and 255
                        if (byte == 255 && index + 2 < count) {
                            val command = buffer[index + 1].toInt() and 255
                            val option = buffer[index + 2].toInt() and 255
                            if (command == 251 || command == 252 || command == 253 || command == 254) {
                                output.write(byteArrayOf(255.toByte(), (if (command == 253 || command == 254) 252 else 254).toByte(), option.toByte()))
                                output.flush()
                                index += 3
                                continue
                            }
                        }
                        if (byte == 10 || byte == 13) {
                            val text = line.toString().trim()
                            if (text.isNotBlank()) processLine(text, prefs.getString("format", "New DX {call} on {frequency} kilohertz").orEmpty())
                            line.setLength(0)
                            prompt.setLength(0)
                        } else if (byte in 32..126 || byte == 9) {
                            if (line.length < 2048) line.append(byte.toChar())
                            prompt.append(byte.toChar())
                            if (prompt.length > 180) prompt.delete(0, prompt.length - 180)
                            val p = prompt.toString().lowercase(Locale.US).trim()
                            if (p != lastPrompt) {
                                if (!loginSent && (p.endsWith("login:") || p.endsWith("callsign:") || p.endsWith("call:"))) {
                                    val call = prefs.getString("call", "").orEmpty()
                                    if (call.isNotBlank()) { output.write((call + "\r\n").toByteArray()); output.flush(); loginSent = true; lastPrompt = p }
                                    else update("Cluster requests a callsign")
                                } else if (!passwordSent && p.endsWith("password:")) {
                                    val pass = prefs.getString("password", "").orEmpty()
                                    if (pass.isNotBlank()) { output.write((pass + "\r\n").toByteArray()); output.flush(); passwordSent = true; lastPrompt = p }
                                    else update("Cluster requests a password")
                                }
                            }
                        }
                        index++
                    }
                }
                connection.close()
            } catch (error: Exception) {
                if (running) update("Connection error: " + (error.message ?: error.javaClass.simpleName))
            } finally { socket = null }
            if (running) {
                update("Disconnected. Retrying in 5 seconds")
                try { Thread.sleep(5000) } catch (_: InterruptedException) { break }
            }
        }
        if (!running) update("Stopped")
    }
    private fun processLine(line: String, template: String) {
        val announcement = formatSpot(line, template) ?: return
        synchronized(spots) {
            spots.add(0, line)
            while (spots.size > 150) spots.removeAt(spots.lastIndex)
        }
        sendBroadcast(Intent(UPDATE).setPackage(packageName))
        speak(announcement)
    }
    override fun onDestroy() {
        running = false
        socket?.close()
        tts?.stop()
        tts?.shutdown()
        status = "Stopped"
        super.onDestroy()
    }
}
