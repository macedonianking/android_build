#include "cygwin.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void *cygwin_create_path(int conv, const char *src)
{
    char *ptr, *dst;
    int n;

    n = strlen(src);
    dst = (char *)malloc(strlen(src) + 1);

    for (ptr = dst; *src != '\0'; ++ptr, ++src)
    {
        *ptr = *src;
        if (*ptr == '/')
            *ptr = '\\';
    }
    *ptr = '\0';

    return dst;
}