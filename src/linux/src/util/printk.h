#ifndef LINUX_SRC_UTIL_PRINTK_H
#define LINUX_SRC_UTIL_PRINTK_H

extern int printk(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
extern void flushk();

#endif
