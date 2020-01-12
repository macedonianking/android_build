#include "test_list.h"

#include <stdio.h>
#include <stdlib.h>

#include "util/list.h"

struct test_entry
{
    struct list_head list;
    int value;
};

static unused struct test_entry *create_test_entry(int n)
{
    struct test_entry *ptr;

    ptr = (struct test_entry *)malloc(sizeof(*ptr));
    INIT_LIST_HEAD(&ptr->list);
    ptr->value = n;

    return ptr;
}

static unused void free_test_entry(struct test_entry *ptr)
{
    free(ptr);
}

/**
 * 测试列表的基本功能
 */
void test_list()
{
    LIST_HEAD(entry_list);
    struct test_entry *ptr;
    struct list_head *pos;

    printf("test_list:\n");

    for (int i = 0; i < 100; ++i)
    {
        ptr = create_test_entry(i);
        list_add_tail(&ptr->list, &entry_list);
    }

    list_for_each_entry(ptr, pos, &entry_list, list)
        printf("%d\n", ptr->value);

    while (!list_empty(&entry_list))
    {
        ptr = list_entry(entry_list.next, struct test_entry, list);

        list_del_init(&ptr->list);
        free_test_entry(ptr);
    }
}