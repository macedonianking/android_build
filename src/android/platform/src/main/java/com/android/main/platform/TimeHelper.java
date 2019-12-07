package com.android.main.platform;


import java.text.SimpleDateFormat;
import java.util.GregorianCalendar;
import java.util.Locale;

public class TimeHelper {
    private static final GregorianCalendar sTime = new GregorianCalendar();
    private static SimpleDateFormat sDayNoFormat;

    /**
     * @param millis
     * @return
     */
    public static synchronized int getDayNo(long millis) {
        GregorianCalendar time = TimeHelper.sTime;
        time.setTimeInMillis(millis);

        if (sDayNoFormat == null) {
            sDayNoFormat = new SimpleDateFormat("yyyyMMDD", Locale.US);
        }
        String dayNoFormat = sDayNoFormat.format(time.getTime());
        return Integer.parseInt(dayNoFormat);
    }
}
