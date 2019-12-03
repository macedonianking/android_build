#ifndef SRC_K_TYPES_H_
#define SRC_K_TYPES_H_
/**
 * 使用的数据类型的一些定义 
 */

#define K_UINT_MAX (~0UL)
#define K_INT_MAX (K_UINT_MAX >> 1)
#define K_INT_MIN (-K_INT_MAX - 1)

#define K_ULONG_MAX (~0UL)
#define K_LONG_MAX (K_ULONG_MAX >> 1)
#define K_LONG_MIN (-K_LONG_MAX - 1)

#define to_hex(v) ((v) < 0xa ? '0' + (v) : 'a' + (v)-0xa)

#define BITS_PER_LONG (sizeof(unsigned long) << 3)

#endif /* SRC_K_TYPES_H_ */
