#include "endian.h"

#include "k_types.h"

void show_bytes(const void *ptr, size_t size)
{
    const unsigned char *p = (const unsigned char *)ptr;
    const char *fmt = "%02x";

    for (int i = 0; i < size; ++i)
    {
        printf(fmt, p[i]);
        fmt = " %02x";
    }
    printf("\n");
}

void show_binary(unsigned long v)
{
    char src_buf[BITS_PER_LONG + 1];
    char dst_buf[BITS_PER_LONG + 1];
    int m, n = 0;
    int i;

    src_buf[n++] = '\0';
    do
    {
        i = v & 0x01;
        v >>= 1;
        src_buf[n++] = i ? '1' : '0';
    } while (v != 0);

    m = 0;
    --n;
    do
    {
        dst_buf[m++] = src_buf[n--];
    } while (n >= 0);

    printf("%s\n", dst_buf);
}

void reverse_array(int buf[], size_t len)
{
    int s, e;

    for (s = 0, e = len - 1; s < e; ++s, --e)
        swap_int(buf + s, buf + e);
}

void chapter2_12()
{
    unsigned int v = 0x87654321U;

    printf("chapter2_12:\n");
    printf("0x%08x\n", v & 0xff);
    printf("0x%08x\n", v ^ ~0xFF);
    printf("0x%08x\n", v | 0xFF);
}
