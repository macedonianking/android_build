#include <stdio.h>
#include <stdlib.h>

#include <stdint.h>
#include <inttypes.h>

#include "endian.h"
#include "hello_shared/hello.h"
#include "hello_static/hello.h"

#include "chapter2/chapter2.h"

static int test_a;
static int test_b;

int a;
int b = 10;

const int test_buf[10] = {[0 ... 9] = 1000};

int main(int argc, char const *argv[])
{
    chapter2_2_22();
    test_a = 1;
    test_b = 2;
    printf("a=%d, b=%d\n", test_a, test_b);
    a = 10;
    printf("a=%d, b=%d\n", a, b);
    hello_world_shared();
    return 0;
}
