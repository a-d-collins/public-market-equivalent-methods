# coding=utf-8


def get_unique_values(list_of_lists, key):
    """
    Given any number of lists or lists of dicts, get list of unique values at given 'key'.
    :param list_of_lists: list of lists
    :param key: index or dictionary key
    :return: list of unique values
    """
    master_list = []
    for list in list_of_lists:
        master_list += list

    return [value for value in set([x[key] for x in master_list])]