#include "util/test_atomic.h"

#include <stdio.h>
#include <stdlib.h>

#include "util/atomic.h"
#include "util/bug.h"

void test_atomic()
{
    atomic_t v = ATOMIC_INIT(0);

    printf("test_atomic:\n");
    atomic_inc(&v);
    atomic_dec(&v);

    atomic_add(100, &v);
    BUG_ON(!atomic_sub_and_test(100, &v));

    atomic_inc(&v);
    BUG_ON(!atomic_dec_and_test(&v));
}