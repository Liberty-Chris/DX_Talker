package club.dxtalker.android

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Bundle
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import com.google.zxing.BarcodeFormat
import com.journeyapps.barcodescanner.BarcodeCallback
import com.journeyapps.barcodescanner.BarcodeResult
import com.journeyapps.barcodescanner.CameraPreview
import com.journeyapps.barcodescanner.DecoratedBarcodeView
import com.journeyapps.barcodescanner.DefaultDecoderFactory

class QrScanActivity : Activity() {
    private var scanner: DecoratedBarcodeView? = null
    private lateinit var message: TextView
    private var failed = false
    private val collection = QrCollection()
    private var completed = false
    private fun progressResult() = Intent().putStringArrayListExtra("qr_pages",collection.saved())
    private fun closeScanner() { if(!completed)setResult(RESULT_CANCELED,progressResult());finish() }
    override fun onSaveInstanceState(out:Bundle) { out.putStringArrayList("qr_pages",collection.saved());super.onSaveInstanceState(out) }
    @Deprecated("Compatibility") override fun onBackPressed() { closeScanner() }
    override fun onCreate(savedInstanceState: Bundle?) {
        setTheme(android.R.style.Theme_Material_NoActionBar)
        super.onCreate(savedInstanceState)
        (savedInstanceState?.getStringArrayList("qr_pages") ?: intent.getStringArrayListExtra("qr_pages"))?.forEach { runCatching { collection.accept(it) } }
        val panel=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setPadding(16,16,16,16);setBackgroundColor(Color.rgb(15,23,31)) }
        panel.setOnApplyWindowInsetsListener { view,insets ->
            if(android.os.Build.VERSION.SDK_INT>=30) {
                val bars=insets.getInsets(android.view.WindowInsets.Type.systemBars())
                view.setPadding(16+bars.left,16+bars.top,16+bars.right,16+bars.bottom)
            } else view.setPadding(16+insets.systemWindowInsetLeft,16+insets.systemWindowInsetTop,16+insets.systemWindowInsetRight,16+insets.systemWindowInsetBottom)
            insets
        }
        message=TextView(this).apply { text="Scan a DX Talker collection QR";setTextColor(Color.WHITE);textSize=18f;setPadding(8,16,8,16);accessibilityLiveRegion=View.ACCESSIBILITY_LIVE_REGION_POLITE }
        panel.addView(message)
        panel.addView(Button(this).apply { text="Close scanner";isAllCaps=false;setOnClickListener { closeScanner() } })
        setContentView(panel)
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            cameraFailure(null,"Camera permission is unavailable. Close and allow camera access before scanning."); return
        }
        try {
            scanner=DecoratedBarcodeView(this).also { preview ->
                preview.barcodeView.decoderFactory=DefaultDecoderFactory(listOf(BarcodeFormat.QR_CODE))
                preview.barcodeView.addStateListener(object:CameraPreview.StateListener {
                    override fun previewSized() {}
                    override fun previewStarted() { MobileDiagnostics.record(this@QrScanActivity,"qr_camera_preview_started") }
                    override fun previewStopped() {}
                    override fun cameraClosed() {}
                    override fun cameraError(error:Exception) { cameraFailure(error,"The camera could not open. Close other camera apps and try again, or import a transfer file.") }
                })
                preview.decodeContinuous(object:BarcodeCallback {
                    override fun barcodeResult(result:BarcodeResult) {
                        if(failed || completed)return
                        try {
                            val data=collection.accept(result.text)
                            if(data!=null) { completed=true;setResult(RESULT_OK,progressResult().putExtra("collection_json",data.toString()));finish() }
                            else message.text="Scanned ${collection.scanned} of ${collection.total} pages. Show the next QR page."
                        }catch(error:Exception) { message.text=(error.message ?: "Invalid QR page")+". Your collected pages are kept." }
                    }
                })
                panel.addView(preview,LinearLayout.LayoutParams(-1,0,1f))
            }
        } catch (error:RuntimeException) { cameraFailure(error,"The scanner could not start. Close it and import a transfer file or export diagnostics.") }
    }
    private fun cameraFailure(error:Exception?, text:String) {
        failed=true;message.text=text
        MobileDiagnostics.record(this,"qr_camera_failed",error)
        scanner?.pause()
    }
    override fun onResume() {
        super.onResume()
        if (!failed) try {
            if(checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) scanner?.resume()
            else cameraFailure(null,"Camera permission was removed. Close and allow camera access before scanning.")
        } catch(error:RuntimeException) { cameraFailure(error,"The camera could not resume. Close the scanner and try again.") }
    }
    override fun onPause() { scanner?.pause();super.onPause() }
}
