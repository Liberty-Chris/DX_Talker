package club.dxtalker.android

import android.app.*
import android.content.Intent
import android.os.IBinder
import android.os.Handler
import android.os.Looper
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import java.net.InetSocketAddress
import java.net.Socket
import java.time.Instant
import java.util.Locale
import kotlin.concurrent.thread

class ListenerService : Service(), TextToSpeech.OnInitListener {
    companion object {
        const val UPDATE="club.dxtalker.android.UPDATE"
        @Volatile var status="Stopped"
        @Volatile var muted=false
        @Volatile var paused=false
        @Volatile var speechReady=false
        @Volatile var listeningActive=false
        val spots=mutableListOf<String>()
        fun formatSpot(line:String,template:String):String?=SpotPolicy.parse(line)?.let{SpotPolicy.speak(it,template,"kHz")}
    }
    private val main=Handler(Looper.getMainLooper())
    private val pending=java.util.ArrayDeque<Pair<String,Instant>>()
    private val seen=mutableMapOf<String,Long>()
    private var speaking=false
    private var nextAllowedAt=0L
    private val speechWake=Runnable { nextSpeech() }
    private var utterance=""
    private var tts:TextToSpeech?=null
    @Volatile private var running=false
    @Volatile private var generation=0
    @Volatile private var socket:Socket?=null
    private var worker:Thread?=null
    @Volatile private var session:Map<String,String> = emptyMap()
    private val prefs by lazy { getSharedPreferences("dx",MODE_PRIVATE) }
    override fun onBind(intent:Intent?):IBinder?=null
    override fun onCreate(){super.onCreate();tts=TextToSpeech(this,this)
        getSystemService(NotificationManager::class.java).createNotificationChannel(NotificationChannel("dx","DX cluster listening",NotificationManager.IMPORTANCE_LOW))
    }
    private fun notification():Notification {
        val open=PendingIntent.getActivity(this,0,Intent(this,MainActivity::class.java),PendingIntent.FLAG_IMMUTABLE)
        val builder=Notification.Builder(this,"dx").setSmallIcon(android.R.drawable.ic_media_play).setContentTitle("DX Talker").setContentText(status).setContentIntent(open)
        for((index,action) in listOf("mute","pause","stop").withIndex()){
            val intent=PendingIntent.getService(this,index+1,Intent(this,ListenerService::class.java).setAction(action),PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            builder.addAction(android.R.drawable.ic_media_play,when(action){"mute"->if(muted)"Unmute" else "Mute";"pause"->if(paused)"Resume" else "Pause";else->"Stop"},intent)
        };return builder.build()
    }
    private fun update(message:String?=null){if(message!=null)status=message
        sendBroadcast(Intent(UPDATE).setPackage(packageName));if(running)getSystemService(NotificationManager::class.java).notify(1,notification())}
    override fun onInit(result:Int){main.post{
        speechReady=result==TextToSpeech.SUCCESS && tts?.setLanguage(Locale.US) in listOf(TextToSpeech.LANG_AVAILABLE,TextToSpeech.LANG_COUNTRY_AVAILABLE,TextToSpeech.LANG_COUNTRY_VAR_AVAILABLE)
        tts?.setOnUtteranceProgressListener(object:UtteranceProgressListener(){
            override fun onStart(id:String?){}
            override fun onDone(id:String?){main.post{if(id!=utterance)return@post;speaking=false;nextAllowedAt=android.os.SystemClock.elapsedRealtime()+setting("spacing_seconds","5").toLong()*1000;nextSpeech()}}
            @Deprecated("TTS callback") override fun onError(id:String?){main.post{if(id!=utterance)return@post;speaking=false;pending.clear();update("Speech failed. Check the installed voice.")}}
        });if(!speechReady)update("Speech unavailable. Install an English system voice.") else{update();nextSpeech()}
    }}
    private fun nextSpeech(){
        if(!speechReady||speaking||paused||muted)return
        val delay=nextAllowedAt-android.os.SystemClock.elapsedRealtime()
        if(delay>0) { main.removeCallbacks(speechWake);main.postDelayed(speechWake,delay);return }
        while(pending.isNotEmpty()){
            val item=pending.removeFirst();if(item.second<Instant.now())continue
            speaking=true;utterance="dx"+System.nanoTime();val result=tts?.speak(item.first,TextToSpeech.QUEUE_FLUSH,null,utterance)
            if(result==TextToSpeech.ERROR){speaking=false;pending.clear();update("Speech failed. Check the system voice.")};break
        }
    }
    private fun clearSpeech(){main.removeCallbacks(speechWake);nextAllowedAt=0;pending.clear();speaking=false;utterance="";tts?.stop()}
    private fun snapshot() = listOf("host","port","call","password","source_type","feed_url","poll_seconds","format","min_khz","max_khz","max_age_seconds","repeat_seconds","spacing_seconds","frequency_unit","filter_bands","filter_modes","filter_activities").mapNotNull { key -> prefs.getString(key,null)?.let { key to it } }.toMap()
    override fun onStartCommand(intent:Intent?,flags:Int,startId:Int):Int {
        if(intent?.action == "switch") {
            running=false;generation++;try { socket?.close() } catch(_:Exception) {};worker?.interrupt();clearSpeech()
            listeningActive=false
            return onStartCommand(Intent(this,ListenerService::class.java).setAction("start"),flags,startId)
        }
        when(intent?.action){
            "apply" -> {
                // Update only listening policy, never an unsaved source or credentials.
                val keys=setOf("format","min_khz","max_khz","max_age_seconds","repeat_seconds","spacing_seconds","frequency_unit","filter_bands","filter_modes","filter_activities")
                val fresh=snapshot(); session=session + fresh.filterKeys { it in keys }; clearSpeech(); seen.clear()
                synchronized(spots) { spots.clear() }; update()
            }
            "start"->if(!running){
                session=snapshot()
                running=true;listeningActive=true;paused=false;generation++;val token=generation;seen.clear();clearSpeech();synchronized(spots){spots.clear()}
                startForeground(1,notification());update("Connecting. Listening armed for the first spot.");worker=thread(name="dx-listener"){listenLoop(token)}}
            "mute"->{muted=!muted;if(muted)clearSpeech();update();nextSpeech()}
            "pause"->{paused=!paused;if(paused)clearSpeech();update();nextSpeech()}
            "test"->{if(muted||paused)update("Resume and unmute before testing speech.")else if(speechReady){clearSpeech();pending.add(SpotPolicy.speak(DxSpot("KF4DBX",java.math.BigDecimal("14025.5"),Instant.now()),prefs.getString("format","New DX on. {frequency} {unit}. {call}.").orEmpty(),prefs.getString("frequency_unit","kHz").orEmpty()) to Instant.now().plusSeconds(120));nextSpeech()}else update("Wait for the speech engine or install an English voice.")}
            "stop"->{running=false;listeningActive=false;generation++;try{socket?.close()}catch(_:Exception){};worker?.interrupt();clearSpeech();update("Stopped");stopForeground(STOP_FOREGROUND_REMOVE);stopSelf()}
        };return START_NOT_STICKY
    }
    private fun active(token:Int)=running&&token==generation
    private fun setting(name:String,default:String)=if(listeningActive)session[name]?:default else prefs.getString(name,default).orEmpty()
    private fun process(line:String,token:Int, supplied:DxSpot?=null){
        if(!active(token))return
        val now=Instant.now();val spot=supplied?:SpotPolicy.parse(line,now)?:return
        main.post{
            if(!active(token))return@post
            if(!SpotFilters.matches(spot) { key -> setting(key,"") } || spot.frequency<setting("min_khz","1").toBigDecimal() || spot.frequency>setting("max_khz","10000000").toBigDecimal())return@post
            synchronized(spots){spots.add(0,spot.call+"  "+spot.frequency(setting("frequency_unit","kHz"))+" "+setting("frequency_unit","kHz"));while(spots.size>150)spots.removeAt(spots.lastIndex)}
            update("Receiving matching DX spots")
            val age=setting("max_age_seconds","180").toLong();val key=spot.call+":"+spot.frequency.stripTrailingZeros().toPlainString();val tick=android.os.SystemClock.elapsedRealtime()
            seen.entries.removeAll{tick-it.value>=setting("repeat_seconds","300").toLong()*1000}
            if(muted||paused||spot.time.plusSeconds(age)<now||spot.frequency<setting("min_khz","1").toBigDecimal()||spot.frequency>setting("max_khz","10000000").toBigDecimal()||key in seen||pending.size>=100)return@post
            seen[key]=tick
            pending.add(SpotPolicy.speak(spot,setting("format","New DX on. {frequency} {unit}. {call}."),setting("frequency_unit","kHz")) to spot.time.plusSeconds(age));nextSpeech()
        }
    }
    private fun failure(error:Exception):String=when(error){
        is java.net.UnknownHostException->"Hostname could not be resolved. Check the cluster address."
        is java.net.ConnectException->"Connection refused or unreachable. Check host, port and cluster availability."
        is java.net.SocketTimeoutException->"Connection timed out. Check the network or try another cluster."
        is javax.net.ssl.SSLException->"Secure feed connection could not be verified. Check the clock and network filtering."
        is LoginFailure->error.message.orEmpty()
        else->"Cluster disconnected or unavailable. Try another cluster if retries continue."
    }
    private class LoginFailure(message:String):Exception(message)
    private fun listenLoop(token:Int){var delay=2L
        while(active(token)){
            try{
                if(setting("source_type","TCP/Telnet")=="HTTPS JSON")https(token) else tcp(token)
            }catch(error:Exception){if(active(token)){
                MobileDiagnostics.record(this,"source_failure",error);update(failure(error)+" Retrying in ${delay}s.")
                main.post{if(active(token))clearSpeech()}
            }}
            if(active(token)){try{Thread.sleep(delay*1000)}catch(_:InterruptedException){break};delay=(delay*2).coerceAtMost(60)}
        }
    }
    private fun tcp(token:Int){
        val connection=Socket();socket=connection
        try{
            val host=setting("host","");val port=setting("port","7373").toInt()
            require(host.isNotBlank()&&port in 1..65535)
            connection.keepAlive=true;connection.connect(InetSocketAddress(host,port),10000);connection.soTimeout=1000
            if(!active(token))return
            update("Connected. Listening for the first spot; sign in may still be required.")
            val decoder=TelnetText();val line=StringBuilder();var overflow=false;var loginSent=false;var passwordSent=false
            val input=connection.getInputStream();val output=connection.getOutputStream();val buffer=ByteArray(4096)
            fun inspect(text:String,complete:Boolean){
                if(Regex("already (connected|logged\\s*in)|duplicate (login|connection)",RegexOption.IGNORE_CASE).containsMatchIn(text))throw LoginFailure("Callsign already connected. Close the other session or use an allowed SSID.")
                if(Regex("invalid password|login failed|access denied|authentication failed",RegexOption.IGNORE_CASE).containsMatchIn(text))throw LoginFailure("Cluster rejected sign in. Check callsign and password.")
                val callPrompt=Regex("(?:login|call\\s*sign|callsign|call|user\\s*name)\\s*[:>]\\s*$",RegexOption.IGNORE_CASE).containsMatchIn(text)
                val passPrompt=Regex("password\\s*[:>]\\s*$",RegexOption.IGNORE_CASE).containsMatchIn(text)
                if(callPrompt&&!loginSent){val call=setting("call","");if(call.isNotBlank()){
                    require(call.length<=20&&call.all{it.isLetterOrDigit()||it in "/-"});output.write((call+"\r\n").toByteArray());output.flush();loginSent=true;if(!complete)line.setLength(0)
                }else update("Cluster requests a callsign. Edit the profile and restart listening.")}
                if(passPrompt&&!passwordSent){val password=SecretStore.reveal(setting("password",""));if(password.isNotEmpty()){
                    require(password.length<=512&&password.all{it.code in 32..126});output.write((password+"\r\n").toByteArray());output.flush();passwordSent=true;if(!complete)line.setLength(0)
                }else update("Cluster requests a password. Edit the profile and restart listening.")}
                if(complete)process(text,token)
            }
            var lastData=android.os.SystemClock.elapsedRealtime();var quietReported=false
            while(active(token)){
                val count=try{input.read(buffer)}catch(_:java.net.SocketTimeoutException){
                    if(!quietReported && android.os.SystemClock.elapsedRealtime()-lastData >= 90000) { update("Connected. No recent cluster data; the feed may be quiet.");quietReported=true }
                    continue
                }
                lastData=android.os.SystemClock.elapsedRealtime();quietReported=false
                if(count<0)throw java.io.EOFException()
                for(c in decoder.feed(buffer,count){output.write(it);output.flush()}){
                    if(c=='\r'||c=='\n'){if(!overflow&&line.isNotBlank())inspect(line.toString(),true);line.setLength(0);overflow=false}
                    else if(!overflow){if(line.length>=2048){line.setLength(0);overflow=true}else{line.append(c);inspect(line.toString(),false)}}
                }
            }
        }finally{try{connection.close()}catch(_:Exception){};if(socket===connection)socket=null}
    }
    private fun https(token:Int){while(active(token)){
        val url=java.net.URL(setting("feed_url",""));require(url.protocol=="https"&&url.userInfo==null)
        val c=url.openConnection() as javax.net.ssl.HttpsURLConnection
        try{c.instanceFollowRedirects=false;c.connectTimeout=10000;c.readTimeout=10000
            val password=SecretStore.reveal(setting("password",""));if(password.isNotBlank())c.setRequestProperty("Authorization","Bearer $password")
            if(c.responseCode!=200)throw LoginFailure(when(c.responseCode){401,403->"Feed denied access. Check the bearer token.";404->"Feed URL was not found.";429->"Feed rate limited requests. Increase polling time.";else->"Feed returned HTTP ${c.responseCode}."})
            val bytes=java.io.ByteArrayOutputStream();c.inputStream.use{input->val buffer=ByteArray(8192);while(true){val n=input.read(buffer);if(n<0)break;bytes.write(buffer,0,n);require(bytes.size()<=1024*1024)}}
            val records=org.json.JSONArray(bytes.toString("UTF-8"));require(records.length()<=2000)
            for(i in 0 until records.length()){val r=records.optJSONObject(i)?:continue
                try{val time=Instant.parse(r.getString("time"));val stamp=java.time.format.DateTimeFormatter.ofPattern("HHmm'Z'").withZone(java.time.ZoneOffset.UTC).format(time)
                    if(time>=Instant.now().minusSeconds(600)&&time<=Instant.now().plusSeconds(120)) {
                        val line="DX de ${r.getString("spotter")}: ${r.getString("frequency_khz")} ${r.getString("dx_call")} $stamp"
                        val parsed=SpotPolicy.parse(line)?.copy(time=time,comment=SpotFilters.clean(r.optString("comment","")),mode=SpotFilters.clean(r.optString("mode","")))
                        if(parsed!=null)process(line,token,parsed)
                    }
                }catch(_:Exception){}
            };update("Feed connected. Listening armed.")
        }finally{c.disconnect()}
        Thread.sleep(setting("poll_seconds","30").toLong().coerceIn(15,3600)*1000)
    }}
    override fun onDestroy(){running=false;listeningActive=false;generation++;worker?.interrupt();try{socket?.close()}catch(_:Exception){};clearSpeech();tts?.shutdown();speechReady=false;status="Stopped";super.onDestroy()}
}
