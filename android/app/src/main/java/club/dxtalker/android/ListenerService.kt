package club.dxtalker.android

import android.app.*
import android.content.Intent
import android.os.IBinder
import android.speech.tts.TextToSpeech
import java.net.Socket
import java.util.Locale
import kotlin.concurrent.thread

class ListenerService : Service(), TextToSpeech.OnInitListener {
    private var tts: TextToSpeech? = null
    @Volatile private var running = false
    @Volatile private var muted = false
    @Volatile private var paused = false
    private var socket: Socket? = null
    override fun onBind(intent: Intent?): IBinder? = null
    override fun onCreate() { super.onCreate(); tts = TextToSpeech(this, this) }
    override fun onInit(status: Int) { if (status == TextToSpeech.SUCCESS) tts?.language = Locale.US }
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            "start" -> {
                if (!running) {
                    val channel = NotificationChannel("dx", "DX announcements", NotificationManager.IMPORTANCE_LOW)
                    getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
                    val pending = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
                    startForeground(1, Notification.Builder(this, "dx").setContentTitle("DX Talker listening")
                        .setContentText("DX cluster monitoring active").setSmallIcon(android.R.drawable.ic_media_play)
                        .setContentIntent(pending).build())
                    running = true
                    thread(name = "dx-cluster", isDaemon = true) { listenLoop() }
                }
            }
            "mute" -> muted = !muted
            "pause" -> paused = !paused
            "stop" -> { running = false; socket?.close(); stopForeground(STOP_FOREGROUND_REMOVE); stopSelf() }
        }
        return START_NOT_STICKY
    }
    private fun listenLoop() {
        val prefs = getSharedPreferences("dx", MODE_PRIVATE)
        while (running) {
            try {
                Socket(prefs.getString("host", "w4mr.ddns.net"), prefs.getString("port", "7373")!!.toInt()).use { conn ->
                    socket = conn
                    val reader = conn.getInputStream().bufferedReader()
                    val writer = conn.getOutputStream().bufferedWriter()
                    while (running) {
                        val line = reader.readLine() ?: break
                        val lower = line.lowercase(Locale.US)
                        if (lower.contains("login:") || lower.contains("callsign:")) {
                            writer.write(prefs.getString("call", "") + "\n"); writer.flush()
                        } else if (lower.contains("password:")) {
                            writer.write(prefs.getString("password", "") + "\n"); writer.flush()
                        } else if (line.startsWith("DX de ", ignoreCase = true) && !muted && !paused) {
                            val match = Regex("^DX de \\S+:\\s+(\\d+(?:\\.\\d+)?)\\s+(\\S+)", RegexOption.IGNORE_CASE).find(line)
                            if (match != null) {
                                val freq = match.groupValues[1]
                                val call = match.groupValues[2]
                                val spoken = prefs.getString("format", "New DX {call} on {frequency}")!!
                                    .replace("{call}", call).replace("{frequency}", freq)
                                tts?.speak(spoken, TextToSpeech.QUEUE_ADD, null, "spot-${System.nanoTime()}")
                            }
                        }
                    }
                }
            } catch (_: Exception) { /* reconnect after network interruption */ }
            if (running) Thread.sleep(5000)
        }
    }
    override fun onDestroy() { running = false; socket?.close(); tts?.stop(); tts?.shutdown(); super.onDestroy() }
}
