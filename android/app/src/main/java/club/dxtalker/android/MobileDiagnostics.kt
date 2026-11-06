package club.dxtalker.android
import android.app.Application
import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

object MobileDiagnostics {
    @Synchronized fun record(context:Context,event:String,error:Throwable?=null) {
        if(!context.getSharedPreferences("dx",Context.MODE_PRIVATE).getBoolean("diagnostics",true))return
        try {
            val dir=File(context.filesDir,"diagnostics").apply{mkdirs()};val file=File(dir,"events.jsonl")
            if(file.length()>512*1024){File(dir,"events.jsonl.2").delete();File(dir,"events.jsonl.1").renameTo(File(dir,"events.jsonl.2"));file.renameTo(File(dir,"events.jsonl.1"))}
            val record=JSONObject().put("time",System.currentTimeMillis()).put("event",event)
            if(error!=null){record.put("error_type",error.javaClass.simpleName);record.put("frames",JSONArray(error.stackTrace.take(30).map{JSONObject().put("file",it.fileName).put("line",it.lineNumber).put("method",it.methodName)}))}
            file.appendText(record.toString()+"\n")
        }catch(_:Exception){}
    }
}
class DxApplication:Application(){
    override fun onCreate(){super.onCreate();val previous=Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler{thread,error->MobileDiagnostics.record(this,"uncaught_exception",error);previous?.uncaughtException(thread,error)}
        try {
            val prefs=getSharedPreferences("dx",Context.MODE_PRIVATE);val editor=prefs.edit()
            val password=prefs.getString("password","").orEmpty()
            if(password.isNotEmpty()&&!password.startsWith("ks1:"))editor.putString("password",SecretStore.protect(password))
            val profiles=org.json.JSONArray(prefs.getString("profiles","[]"))
            for(i in 0 until profiles.length()){val p=profiles.getJSONObject(i);val value=p.optString("password")
                if(value.isNotEmpty()&&!value.startsWith("ks1:"))p.put("password",SecretStore.protect(value))}
            editor.putString("profiles",profiles.toString()).commit()
        }catch(error:Exception){MobileDiagnostics.record(this,"credential_migration_failed",error)}
        MobileDiagnostics.record(this,"startup")
    }
}
