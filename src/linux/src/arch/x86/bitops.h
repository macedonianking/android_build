#ifndef LINUX_SRC_ARCH_X86_BITOPS_H
#define LINUX_SRC_ARCH_X86_BITOPS_H

#include "config/config.h"
#include "config/compiler.h"

#define LOCK_PREFIX "lock; "

static inline void __set_bit(int nr, unsigned long *addr)
{
    asm volatile("bts %1, %0;"
                 : "=m"(*addr)
                 : "Ir"(nr));
}

static inline void set_bit(int nr, unsigned long *addr)
{
    asm volatile(LOCK_PREFIX "bts %1, %0;"
                 : "=m"(*addr)
                 : "Ir"(nr)
                 : "memory");
}

static inline int test_and_set_bit(int nr, unsigned long *addr)
{
    unsigned char r;
    asm volatile(LOCK_PREFIX "bts %2, %0;"
                             "setc %b1;"
                 : "=m"(*addr), "=q"(r)
                 : "Ir"(nr)
                 : "memory");
    return r;
}

extern int find_first_bit(const unsigned long *addr, int size);
extern int find_next_bit(const unsigned long *addr, int size, int offset);
extern int find_first_zero_bit(const unsigned long *addr, int size);
extern int find_next_zero_bit(const unsigned long *addr, int size, int offset);

#endif