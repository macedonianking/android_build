#include "chapter2.h"

#include "endian.h"

void chapter2_2_3()
{
    short v = 12345;
    short k = -v;

    show_bytes(&v, sizeof(v));
    show_bytes(&k, sizeof(k));
}

void chapter2_2_22()
{
    short s = -12345;
    unsigned v = s;

    show_bytes(&s, sizeof(s));
    show_bytes(&v, sizeof(v));
}