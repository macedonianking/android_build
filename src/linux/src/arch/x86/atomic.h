#ifndef LINUX_SRC_ARCH_X86_ATOMIC_H
#define LINUX_SRC_ARCH_X86_ATOMIC_H

#include "config/config.h"
#include "config/compiler.h"

#define LOCK "lock; "

typedef struct
{
    volatile int counter;
} atomic_t;

#define ATOMIC_INIT(x) \
    {                  \
        (x)            \
    }

#define atomic_set(v, i)    \
    do                      \
    {                       \
        (v)->counter = (i); \
    } while ()
#define atomic_read(v) ((v)->counter)

static inline void atomic_inc(atomic_t *v)
{
    asm volatile(LOCK "incl %0;"
                 : "=m"(v->counter)
                 :
                 : "memory");
}

static inline void atomic_dec(atomic_t *v)
{
    asm volatile(LOCK "decl %0;"
                 : "=m"(v->counter)
                 :
                 : "memory");
}

static inline void atomic_add(int i, atomic_t *v)
{
    asm volatile(LOCK "addl %1, %0;"
                 : "=m"(v->counter)
                 : "Ir"(i)
                 : "memory");
}

static inline void atomic_sub(int i, atomic_t *v)
{
    asm volatile(LOCK "subl %1, %0;"
                 : "=m"(v->counter)
                 : "Ir"(i)
                 : "memory");
}

static inline int atomic_add_return(int i, atomic_t *v)
{
    asm volatile(LOCK "xaddl %1, %0;"
                 : "=m"(v->counter)
                 : "r"(i)
                 : "memory");
    return i;
}

#define atomic_sub_return(i, v) atomic_add_return(-(i), (v))
#define atomic_inc_return(v) atomic_inc_return(1, (v))
#define atomic_dec_return(v) atomic_inc_return(-1, (v))

static inline int atomic_add_and_test(int i, atomic_t *v)
{
    unsigned char r;
    asm volatile(LOCK "addl %2, %0;"
                      "setz %b1;"
                 : "=m"(v->counter), "=q"(r)
                 : "Ir"(i)
                 : "memory");
    return r;
}

#define atomic_sub_and_test(i, v) atomic_add_and_test(-(i), (v))

static inline int atomic_inc_and_test(atomic_t *v)
{
    unsigned char r;
    asm volatile(LOCK "incl %0;"
                      "setz %b1;"
                 : "=m"(v->counter), "=q"(r)
                 :
                 : "memory");
    return r;
}

static inline int atomic_dec_and_test(atomic_t *v)
{
    unsigned char r;
    asm volatile(LOCK "decl %0;"
                      "setz %b1;"
                 : "=m"(v->counter), "=q"(r)
                 :
                 : "memory");
    return r;
}

static inline int atomic_add_negative(int i, atomic_t *v)
{
    unsigned char r;
    asm volatile(LOCK "addl %2, %0;"
                      "sets %b1;"
                 : "=m"(v->counter), "=q"(r)
                 : "Ir"(i)
                 : "memory");
    return r;
}

#endif
