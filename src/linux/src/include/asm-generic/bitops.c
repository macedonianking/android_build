#include "include/asm-generic/bitops.h"

#include "asm/bitops.h"

#ifndef ARCH_BITOPS_NWEIGHT_32

int nweight_32(unsigned long v)
{
    int n = 0;

    while (v)
    {
        v &= v - 1;
        ++n;
    }

    return n;
}

#endif
