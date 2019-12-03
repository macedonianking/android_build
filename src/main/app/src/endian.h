#ifndef ENDIAN_H_
#define ENDIAN_H_

#include <stdio.h>

extern void show_bytes(const void *ptr, size_t size);
extern void show_binary(unsigned long v);

extern void reverse_array(int *array, size_t len);

extern void chapter2_12();

static inline void show_int(int v)
{
    show_bytes(&v, sizeof(int));
}

static inline void show_long(long v)
{
    show_bytes(&v, sizeof(long));
}

static inline void show_float(float v)
{
    show_bytes(&v, sizeof(float));
}

static inline void show_double(double v)
{
    show_bytes(&v, sizeof(double));
}

static inline void show_pointer(const void *p)
{
    show_bytes((const void *)&p, sizeof(p));
}

static inline void swap_int(int *a, int *b)
{
    int t;

    t = *a;
    *a = *b;
    *b = t;
}

#endif // ENDIAN_H_