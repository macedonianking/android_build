#include <stdio.h>
#include <stdlib.h>

#include "util/test_list.h"
#include "util/test_atomic.h"

int main(int argc, char const *argv[])
{
    test_list();
    test_atomic();

    return 0;
}
