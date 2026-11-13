package br.com.trackfit;

import android.app.*;
import android.os.*;
import android.webkit.*;
import android.view.WindowManager;
import java.net.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.*;
import org.json.*;

/** Local-only interface. Remote sites never run inside this privileged WebView. */
public class MainActivity extends Activity {
    private WebView web;
    private FinishDrafts finishDrafts;
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        finishDrafts = new FinishDrafts(this);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE);
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG);
        web = new WebView(this);
        web.setPadding(0,0,0,0);
        web.setOnApplyWindowInsetsListener((v,insets) -> {
            v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());
            return insets;
        });
        web.getSettings().setJavaScriptEnabled(true);
        web.getSettings().setDomStorageEnabled(false);
        web.getSettings().setAllowFileAccess(false);
        web.getSettings().setAllowContentAccess(false);
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) { return true; }
            @Override public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest r) {
                String path = r.getUrl().getPath();
                if ("https".equals(r.getUrl().getScheme()) && "app.trackfit.local".equals(r.getUrl().getHost()) && ("/index.html".equals(path) || "/app.js".equals(path) || "/style.css".equals(path))) {
                    try { return new WebResourceResponse(path.endsWith(".js") ? "application/javascript" : path.endsWith(".css") ? "text/css" : "text/html", "utf-8", getAssets().open(path.substring(1))); }
                    catch (IOException ignored) { }
                }
                return new WebResourceResponse("text/plain", "utf-8", new ByteArrayInputStream(new byte[0]));
            }
        });
        web.addJavascriptInterface(new Bridge(), "TrackFitNative");
        setContentView(web);
        web.loadUrl("https://app.trackfit.local/index.html");
        NotificationManager manager = getSystemService(NotificationManager.class);
        manager.createNotificationChannel(new NotificationChannel("reviews", "Fichas para revisar", NotificationManager.IMPORTANCE_DEFAULT));
        if (Build.VERSION.SDK_INT >= 33) requestPermissions(new String[]{"android.permission.POST_NOTIFICATIONS"},1);
    }
    private String photoRequest;
    private void photoResult(String request, String text) {
        if(web != null) web.evaluateJavascript("window.equipmentPhotoResult("+JSONObject.quote(request)+","+JSONObject.quote(text)+")",null);
    }
    @Override protected void onActivityResult(int code,int result,android.content.Intent data) {
        super.onActivityResult(code,result,data);
        if((code!=42 && code!=43) || photoRequest==null)return;
        final String request=photoRequest;
        photoRequest=null;
        if(code==43){
            android.net.Uri uri=result==RESULT_OK && data!=null?data.getData():null;
            executor.execute(()->{
                String encoded="";
                if(uri!=null)try{
                    android.graphics.BitmapFactory.Options opt=new android.graphics.BitmapFactory.Options();
                    opt.inJustDecodeBounds=true;
                    try(InputStream in=getContentResolver().openInputStream(uri)){android.graphics.BitmapFactory.decodeStream(in,null,opt);}
                    opt.inJustDecodeBounds=false;opt.inSampleSize=1;
                    while(Math.max(opt.outWidth,opt.outHeight)/opt.inSampleSize>900)opt.inSampleSize*=2;
                    android.graphics.Bitmap bmp;
                    try(InputStream in=getContentResolver().openInputStream(uri)){bmp=android.graphics.BitmapFactory.decodeStream(in,null,opt);}
                    if(bmp!=null){
                        ByteArrayOutputStream out=new ByteArrayOutputStream();bmp.compress(android.graphics.Bitmap.CompressFormat.JPEG,65,out);bmp.recycle();
                        if(out.size()<=165000)encoded=android.util.Base64.encodeToString(out.toByteArray(),android.util.Base64.NO_WRAP);
                    }
                }catch(Exception ignored){}
                String script="window.visualPhotoResult("+JSONObject.quote(request)+","+JSONObject.quote(encoded)+")";
                runOnUiThread(()->{if(web!=null)web.evaluateJavascript(script,null);});
            });return;
        }
        if(result!=RESULT_OK || data==null || data.getData()==null){photoResult(request,"");return;}
        try {
            com.google.mlkit.vision.common.InputImage image=com.google.mlkit.vision.common.InputImage.fromFilePath(this,data.getData());
            com.google.mlkit.vision.text.TextRecognizer reader=com.google.mlkit.vision.text.TextRecognition.getClient(
                com.google.mlkit.vision.text.latin.TextRecognizerOptions.DEFAULT_OPTIONS);
            reader.process(image).addOnSuccessListener(t->photoResult(request,t.getText().substring(0,Math.min(2000,t.getText().length()))))
                .addOnFailureListener(e->photoResult(request,"")).addOnCompleteListener(t->reader.close());
        } catch(Exception e){photoResult(request,"");}
    }
    private class Bridge {
        @JavascriptInterface public void selectEquipmentPhoto(String request) { choosePhoto(request,42); }
        @JavascriptInterface public void selectVisualPhoto(String request) { choosePhoto(request,43); }
        private void choosePhoto(String request,int code) {
            if(request==null || !request.matches("[a-fA-F0-9-]{36}"))return;
            runOnUiThread(()->{
                photoRequest=request;
                android.content.Intent chooser=new android.content.Intent(android.content.Intent.ACTION_OPEN_DOCUMENT)
                    .addCategory(android.content.Intent.CATEGORY_OPENABLE).setType("image/*");
                try {startActivityForResult(chooser,code);}
                catch(android.content.ActivityNotFoundException e){photoRequest=null;photoResult(request,"");}
            });
        }
        @JavascriptInterface public String lastServer() {
            return getSharedPreferences("connection", MODE_PRIVATE).getString("origin", "");
        }
        @JavascriptInterface public void rememberServer(String origin) {
            if (origin != null && origin.length() <= 2048)
                getSharedPreferences("connection", MODE_PRIVATE).edit().putString("origin", origin).apply();
        }
        @JavascriptInterface public void openVideo(String id) {
            if (id != null && id.matches("[A-Za-z0-9_-]{11}"))
                runOnUiThread(() -> startActivity(new android.content.Intent(MainActivity.this, VideoActivity.class).putExtra("video", id)));
        }
        @JavascriptInterface public boolean storeFinish(String scope,String body) {
            return finishDrafts.write(scope,body);
        }
        @JavascriptInterface public String loadFinish(String scope) {
            return finishDrafts.read(scope);
        }
        @JavascriptInterface public void request(String id, String origin, String token, String method, String path, String body) {
            executor.execute(() -> {
                JSONObject response = new JSONObject();
                HttpURLConnection connection = null;
                try {
                    URI uri = URI.create(origin);
                    if ((!"https".equals(uri.getScheme()) && !(BuildConfig.DEBUG && "http".equals(uri.getScheme()))) || uri.getHost()==null || uri.getUserInfo()!=null || uri.getQuery()!=null || uri.getFragment()!=null || (uri.getPath()!=null && !uri.getPath().isEmpty() && !uri.getPath().equals("/"))) throw new IOException("Endereço do servidor inválido.");
                    if (!path.matches("/[a-zA-Z0-9_/\\-]*") || path.contains("//") || !(method.equals("GET") || method.equals("POST"))) throw new IOException("Requisição inválida.");
                    connection = (HttpURLConnection)new URL(origin.replaceAll("/+$", "")+path).openConnection();
                    connection.setInstanceFollowRedirects(false);
                    connection.setConnectTimeout(10000); connection.setReadTimeout(45000);
                    connection.setRequestMethod(method);
                    connection.setRequestProperty("Authorization", "Bearer "+token);
                    connection.setRequestProperty("Content-Type", "application/json");
                    if (method.equals("POST")) {
                        connection.setDoOutput(true);
                        try (OutputStream out=connection.getOutputStream()) { out.write(body.getBytes(StandardCharsets.UTF_8)); }
                    }
                    int code=connection.getResponseCode();
                    InputStream input=code>=200 && code<300 ? connection.getInputStream() : connection.getErrorStream();
                    String text="{}";
                    if (input != null) {
                        try (InputStream in=input; ByteArrayOutputStream bytes=new ByteArrayOutputStream()) {
                            byte[] buffer=new byte[4096]; int n;
                            while ((n=in.read(buffer))!=-1) { bytes.write(buffer,0,n); if(bytes.size()>2000000) throw new IOException("Resposta muito grande."); }
                            text=bytes.toString("UTF-8");
                        }
                    }
                    response.put("status",code); response.put("body",new JSONTokener(text).nextValue());
                } catch (Exception e) {
                    try { response.put("status",0); response.put("body",new JSONObject().put("detail","Não foi possível conectar ao servidor. Confira o endereço e a conexão.")); } catch(JSONException ignored) {}
                } finally { if(connection!=null) connection.disconnect(); }
                String script="window.receiveNative("+JSONObject.quote(id)+","+response.toString()+")";
                runOnUiThread(() -> { if(web!=null) web.evaluateJavascript(script,null); });
            });
        }
        @JavascriptInterface public void enableReviewPush(String binding) {
            if (!binding.matches("[a-fA-F0-9-]{36}")) return;
            runOnUiThread(() -> {
                if (!getSystemService(NotificationManager.class).areNotificationsEnabled()) {
                    pushResult(binding, "", "Ative a permissão de notificações nas configurações do Android.");
                    return;
                }
                if (com.google.firebase.FirebaseApp.getApps(MainActivity.this).isEmpty()) {
                    pushResult(binding, "", "Esta compilação ainda não está vinculada ao Firebase.");
                    return;
                }
                com.google.firebase.messaging.FirebaseMessaging.getInstance().getToken()
                    .addOnCompleteListener(task -> pushResult(binding,task.isSuccessful()?task.getResult():"",
                                           task.isSuccessful()?"":"Falha ao registrar o aparelho. Tente novamente."));
            });
        }
        @JavascriptInterface public void bindPush(String binding) {
            if (binding.isEmpty() || binding.matches("[a-fA-F0-9-]{36}"))
                getSharedPreferences("push",MODE_PRIVATE).edit().putString("binding",binding).commit();
        }
        @JavascriptInterface public void notifyReview(String id) {
            runOnUiThread(() -> ReviewMessages.show(MainActivity.this,id));
        }
    }
    private void pushResult(String binding,String value,String error) {
        if (web!=null) web.evaluateJavascript("window.receivePush("+JSONObject.quote(binding)+","+
            JSONObject.quote(value)+","+JSONObject.quote(error)+")", null);
    }
    @Override protected void onDestroy() { if(web!=null) { web.removeJavascriptInterface("TrackFitNative"); web.destroy(); web=null; } executor.shutdownNow(); super.onDestroy(); }
}
