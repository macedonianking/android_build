#ifndef LINUX_SRC_CONFIG_COMPILER_H
#define LINUX_SRC_CONFIG_COMPILER_H

#define unused __attribute__((unused))

#define barrier() asm volatile("" \
                               :  \
                               :  \
                               : "memory")

#endif
