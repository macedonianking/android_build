#ifndef LINUX_SRC_INCLUDE_ASM_GENERIC_H
#define LINUX_SRC_INCLUDE_ASM_GENERIC_H

#include "asm/bitops.h"

#ifndef ARCH_BITOPS_NWEIGHT_32
extern int nweight_32(unsigned long);
#endif

#endif