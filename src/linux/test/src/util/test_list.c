#include "test_list.h"

#include <stdio.h>
#include <stdlib.h>

#include "util/list.h"
#include "util/bug.h"

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
    int dst_total, src_total;

    printf("test_list:\n");

    src_total = 0;
    for (int i = 0; i < 100; ++i)
    {
        ptr = create_test_entry(i);
        src_total += ptr->value;

        list_add_tail(&ptr->list, &entry_list);
    }

    dst_total = 0;
    list_for_each_entry(ptr, pos, &entry_list, list)
    {
        dst_total += ptr->value;
    }

    while (!list_empty(&entry_list))
    {
        ptr = list_entry(entry_list.next, struct test_entry, list);

        list_del_init(&ptr->list);
        free_test_entry(ptr);
    }

    BUG_ON(src_total != dst_total);
}