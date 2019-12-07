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
    }
}
