package com.oppo.main.build.util;


import android.view.View;

public class Views {

    /**
     * @param view
     * @param id
     * @param <T>
     * @return
     */
    @SuppressWarnings("unchecked")
    public static <T extends View> T findViewById(View view, int id) {
        return (T) view.findViewById(id);
    }

    /**
     * @param view
     * @param id
     * @param listener
     */
    public static void setViewClickListener(View view, int id, View.OnClickListener listener) {
        view.findViewById(id).setOnClickListener(listener);
    }

}
