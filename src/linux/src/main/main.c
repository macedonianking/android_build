
#include <stdio.h>
#include <stdlib.h>

#include "config/config.h"
#include "config/compiler.h"
#include "util/list.h"

void unused test()
{
    printf("Hello world!!!\n");
}

int main(int argc, char const *argv[])
{
    test();

    return 0;
}
