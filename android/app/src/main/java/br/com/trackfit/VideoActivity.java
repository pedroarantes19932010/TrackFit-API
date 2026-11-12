package br.com.trackfit;

import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.net.Uri;
import android.webkit.*;
import android.widget.*;

/** Isolated player. No native bridge, authentication token or local file access. */
public class VideoActivity extends Activity {
    private WebView player;
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        String id = getIntent().getStringExtra("video");
        if (id == null || !id.matches("[A-Za-z0-9_-]{11}")) { finish(); return; }
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        setContentView(layout);
        Button back = new Button(this);
        back.setText("Voltar à ficha");
        back.setOnClickListener(v -> finish());
        layout.addView(back);
        player = new WebView(this);
        layout.addView(player, new LinearLayout.LayoutParams(-1,0,1));
        player.getSettings().setAllowFileAccess(false);
        player.getSettings().setAllowContentAccess(false);
        player.getSettings().setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        player.getSettings().setJavaScriptEnabled(true);
        player.getSettings().setDomStorageEnabled(true);
        player.setWebChromeClient(new WebChromeClient());
        player.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return request.isForMainFrame() || !"https".equals(request.getUrl().getScheme());
            }
        });
        String html = "<meta name='viewport' content='width=device-width,initial-scale=1'><style>body{margin:0}iframe{width:100%;height:100%;border:0}</style>"
            + "<iframe title='Vídeo do exercício' referrerpolicy='strict-origin-when-cross-origin' src='https://www.youtube.com/embed/" + id + "' allowfullscreen></iframe>";
        player.loadDataWithBaseURL("https://" + getPackageName() + "/",html,"text/html","UTF-8",null);
        Button external = new Button(this);
        external.setText("Abrir no YouTube");
        external.setOnClickListener(v -> {
            try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse("https://www.youtube.com/watch?v="+id))); }
            catch (android.content.ActivityNotFoundException e) { Toast.makeText(this,"Nenhum navegador disponível.",Toast.LENGTH_SHORT).show(); }
        });
        layout.addView(external);
    }
    @Override public void onDestroy() {
        if (player != null) { player.stopLoading(); player.destroy(); }
        super.onDestroy();
    }
}
