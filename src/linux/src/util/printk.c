#include "util/printk.h"

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>

int __attribute__((format(printf, 1, 2))) printk(const char *fmt, ...)
{
    va_list arg_list;
    int n;

    va_start(arg_list, fmt);
    n = vprintf(fmt, arg_list);
    va_end(arg_list);

    return n;
}

void flushk()
{
    fflush(stdout);
    fflush(stderr);
}