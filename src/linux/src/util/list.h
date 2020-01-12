#ifndef SRC_MAIN_UTIL_LIST_H
#define SRC_MAIN_UTIL_LIST_H

#include "util/kernel.h"

#define LIST_POISON1 ((void *)0x00100100)
#define LIST_POISON2 ((void *)0x00200200)

struct list_head
{
    struct list_head *next;
    struct list_head *prev;
};

#define LIST_HEAD(name) struct list_head name = {.next = &(name), .prev = &(name)}

#define INIT_LIST_HEAD(ptr)                \
    do                                     \
    {                                      \
        (ptr)->next = (ptr)->prev = (ptr); \
    } while (0)

static inline void __list_add(struct list_head *prev,
                              struct list_head *next,
                              struct list_head *curr)
{
    next->prev = curr;
    curr->next = next;
    curr->prev = prev;
    prev->next = curr;
}

static inline void list_add(struct list_head *curr,
                            struct list_head *list)
{
    __list_add(list, list->next, curr);
}

static inline void list_add_tail(struct list_head *curr,
                                 struct list_head *list)
{
    __list_add(list->prev, list, curr);
}

static inline int list_empty(struct list_head *list)
{

    return list->next == list;
}

static inline int list_empty_careful(struct list_head *list)
{
    return list->next == list && list->prev == list;
}

static inline void __list_del(struct list_head *prev,
                              struct list_head *next)
{
    next->prev = prev;
    prev->next = next;
}

static inline void list_del(struct list_head *list)
{
    __list_del(list->prev, list->next);
    list->next = (struct list_head *)LIST_POISON1;
    list->prev = (struct list_head *)LIST_POISON2;
}

static inline void list_del_init(struct list_head *list)
{
    __list_del(list->prev, list->next);
    INIT_LIST_HEAD(list);
}

static inline void list_move(struct list_head *list,
                             struct list_head *head)
{
    __list_del(list->prev, list->next);
    list_add(list, head);
}

static inline void list_move_tail(struct list_head *list,
                                  struct list_head *head)
{
    __list_del(list->prev, list->next);
    list_add_tail(list, head);
}

#define list_entry(ptr, type, member) container_of(ptr, type, member)

#define list_for_each(ptr, head) \
    for (ptr = (head); ptr = ptr->next && ptr != (head);)

#define list_for_each_entry(tpos, pos, head, member) \
    for (pos = (head)->next;                         \
         pos != (head) && ({ tpos = list_entry(pos, typeof(*tpos), member); 1; });                     \
         pos = pos->next)
#define list_for_each_entry_safe(tpos, pos, head, member) \
    for (pos = (head)->next;                              \
         pos != (head) && ({ tpos = list_entry(pos, typeof(*tpos), member); \
         pos = pos->next; 1; });)

#endif
