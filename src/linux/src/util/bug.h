#ifndef LINUX_SRC_UTIL_BUG_H
#define LINUX_SRC_UTIL_BUG_H

#include "config/config.h"
#include "config/compiler.h"

#include "util/printk.h"

#define BUG_FATAL()             \
    do                          \
    ({                          \
        *(int *)0 = 0xbeadbeef; \
    }) while (0)

#define BUG_ON(condition)                              \
    do                                                 \
    {                                                  \
        if (condition)                                 \
        {                                              \
            printk("FATAL: BUG_ON("##condition ")\n"); \
            flushk();                                  \
            BUG_FATAL();                               \
        }                                              \
    } while (0)

#endif
