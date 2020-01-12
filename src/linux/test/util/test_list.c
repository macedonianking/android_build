#include "test_list.h"

#include <stdio.h>
#include <stdlib.h>

#include "util/list.h"

struct test_entry
{
    struct list_head list;
    int value;
};

static struct test_entry *create_test_entry(int n)
{
    struct test_entry *ptr;

    ptr = (struct test_entry *)malloc(sizeof(*ptr));
    INIT_LIST_HEAD(&ptr->list);
    ptr->value = n;

    return ptr;
}

static void free_test_entry(struct test_entry *ptr)
{
    free(ptr);
}

void test_list()
{
}