package br.com.trackfit;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;

public class ReviewMessages extends FirebaseMessagingService {
    @Override public void onMessageReceived(RemoteMessage message) {
        String binding = message.getData().get("binding");
        String event = message.getData().get("event");
        if (binding == null || event == null || !event.matches("[a-fA-F0-9-]{36}")) return;
        if (!binding.equals(getSharedPreferences("push", MODE_PRIVATE).getString("binding",""))) return;
        show(this,event);
    }

    static void show(Context context,String event) {
        NotificationManager manager=context.getSystemService(NotificationManager.class);
        if (!manager.areNotificationsEnabled()) return;
        manager.createNotificationChannel(new NotificationChannel("reviews","Fichas para revisar",NotificationManager.IMPORTANCE_DEFAULT));
        Intent intent=new Intent(context,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent open=PendingIntent.getActivity(context,0,intent,PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        Notification note=new Notification.Builder(context,"reviews").setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("TrackFit • revisão disponível").setContentText("Abra o aplicativo para revisar a ficha.")
            .setContentIntent(open).setAutoCancel(true).setOnlyAlertOnce(true).build();
        // Same identifier for a retry and for the foreground inbox.
        manager.notify(event,1,note);
    }
}
