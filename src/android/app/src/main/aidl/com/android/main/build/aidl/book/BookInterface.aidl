// BookInterface.aidl
package com.android.main.build.aidl.book;

import com.android.main.build.entity.Book;

// Declare any non-default types here with import statements

interface BookInterface {

    Book getBook(String bookId);

    /**
     * Demonstrates some basic types that you can use as parameters
     * and return values in AIDL.
     */
    void deleteBook(String bookId);
}
