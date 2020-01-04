package com.android.main.build;

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;

/**
 * @author LiHongbing
 * @since 2019-11-24
 */
public class MainActivity extends Activity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        TextView view = (TextView) findViewById(R.id.dayno);
        // int dayNo = TimeHelper.getDayNo(System.currentTimeMillis());
        view.setText("A");
        view.setText(this.stringFromJNI());
    }

    // Used to load the 'native-lib' library on application startup.
    static {
        System.loadLibrary("nativelib");
    }

    /**
     * A native method that is implemented by the 'native-lib' native library,
     * which is packaged with this application.
     */
    public native String stringFromJNI();
}
