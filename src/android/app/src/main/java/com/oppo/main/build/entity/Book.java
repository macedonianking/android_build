package com.oppo.main.build.entity;

import android.os.Parcel;
import android.os.Parcelable;

public class Book implements Parcelable {

    private String mTitle;
    private float mPrice;

    public Book() {
    }


    @Override
    public int describeContents() {
        return 0;
    }

    @Override
    public void writeToParcel(Parcel dest, int flags) {
        dest.writeString(mTitle);
        dest.writeFloat(mPrice);
    }

    public static final Creator<Book> CREATOR = new Creator<Book>() {
        @Override
        public Book createFromParcel(Parcel in) {
            Book item = new Book();
            item.mTitle = in.readString();
            item.mPrice = in.readFloat();
            return item;
        }

        @Override
        public Book[] newArray(int size) {
            return new Book[size];
        }
    };
}
