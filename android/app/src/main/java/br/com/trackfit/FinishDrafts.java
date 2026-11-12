package br.com.trackfit;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.security.MessageDigest;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** A pending save survives a restart. Each encrypted record is bound to its scope. */
final class FinishDrafts {
    private final SharedPreferences records;
    private static final String KEY = "trackfit.finish.v1";
    FinishDrafts(Context context) {
        records = context.getSharedPreferences(KEY, Context.MODE_PRIVATE);
    }
    private String address(String scope) throws Exception {
        if (scope.isEmpty() || scope.length() > 2048) throw new IllegalArgumentException();
        return Base64.encodeToString(MessageDigest.getInstance("SHA-256")
            .digest(scope.getBytes(StandardCharsets.UTF_8)), Base64.NO_WRAP);
    }
    private static synchronized SecretKey key() throws Exception {
        KeyStore store = KeyStore.getInstance("AndroidKeyStore");
        store.load(null);
        if (!store.containsAlias(KEY)) {
            KeyGenerator generator = KeyGenerator.getInstance("AES", "AndroidKeyStore");
            generator.init(new KeyGenParameterSpec.Builder(KEY,
                KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build());
            return generator.generateKey();
        }
        return (SecretKey) store.getKey(KEY, null);
    }
    boolean write(String scope,String data) {
        try {
            String id = address(scope);
            if (data.isEmpty()) return records.edit().remove(id).commit();
            if (data.length() > 18000) return false;
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE,key());
            cipher.updateAAD(id.getBytes(StandardCharsets.UTF_8));
            String record = Base64.encodeToString(cipher.getIV(),Base64.NO_WRAP) + "." +
                Base64.encodeToString(cipher.doFinal(data.getBytes(StandardCharsets.UTF_8)),Base64.NO_WRAP);
            return records.edit().putString(id, record).commit();
        } catch(Exception failure) { return false; }
    }
    String read(String scope) {
        try {
            String id=address(scope), record=records.getString(id,null);
            if(record==null) return "";
            String[] pieces=record.split("[.]",2);
            Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE,key(),new GCMParameterSpec(128,Base64.decode(pieces[0],Base64.NO_WRAP)));
            cipher.updateAAD(id.getBytes(StandardCharsets.UTF_8));
            return new String(cipher.doFinal(Base64.decode(pieces[1],Base64.NO_WRAP)),StandardCharsets.UTF_8);
        } catch(Exception failure) { return "!"; }
    }
}
