#ifndef LINUX_SRC_UTIL_KERNEL_H
#define LINUX_SRC_UTIL_KERNEL_H

#include "config/config.h"
#include "config/compiler.h"

#define container_of(ptr, type, member) ({                               \
    const typeof(((type *)(0))->member) *__ptr = &((type *)(0))->member; \
    (type *)((char *)(ptr) - (char *)(__ptr));                           \
})

#endif
