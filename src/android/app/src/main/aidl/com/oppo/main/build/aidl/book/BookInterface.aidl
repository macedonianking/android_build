// BookInterface.aidl
package com.oppo.main.build.aidl.book;

import com.oppo.main.build.entity.Book;

// Declare any non-default types here with import statements

interface BookInterface {

    Book getBook(String bookId);

    /**
     * Demonstrates some basic types that you can use as parameters
     * and return values in AIDL.
     */
    void deleteBook(String bookId);
}
