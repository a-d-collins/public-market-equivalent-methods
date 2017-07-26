import bisect


class BisectHelpers(object):
    """
    Helper functions for operating on sorted lists (utilizing the bisect.py Python library). The source for the core
    code in the first 5 functions can be found at the following location in the Python documentation:
    https://docs.python.org/2/library/bisect.html#searching-sorted-lists
    """
    def index(self, a, x):
        'Locate the leftmost value exactly equal to x. If '
        i = bisect.bisect_left(a, x)
        if i != len(a) and a[i] == x:
            return i
        else:
            return None

    def find_lt(self, a, x):
        'Find rightmost value less than x'
        i = bisect.bisect_left(a, x)
        if i:
            return a[i - 1]
        else:
            return None

    def find_le(self, a, x):
        'Find rightmost value less than or equal to x'
        i = bisect.bisect_right(a, x)
        if i:
            return a[i - 1]
        else:
            return None

    def find_gt(self, a, x):
        'Find leftmost value greater than x'
        i = bisect.bisect_right(a, x)
        if i != len(a):
            return a[i]
        else:
            return None

    def find_ge(self, a, x):
        'Find leftmost item greater than or equal to x'
        i = bisect.bisect_left(a, x)
        if i != len(a):
            return a[i]
        else:
            return None

    def index_by_key(self, a, x, key):
        'Locate the leftmost item within list of dicts or lists with specific value exactly equal to x'
        specific_value_list = [item[key] for item in a]

        i = bisect.bisect_left(specific_value_list, x)
        if i != len(a) and a[i] == x:
            return i
        else:
            return None

    def find_eq_by_key(self, a, x, key):
        'Find leftmost item within list of dicts or lists with specific value exactly equal to (eq) x'
        specific_value_list = [item[key] for item in a]

        i = bisect.bisect_left(specific_value_list, x)
        if i != len(a) and a[i][key] == x:
            return a[i]
        else:
            return None

    def find_lt_by_key(self, a, x, key):
        'Find rightmost item within list of dicts or lists with specific value less than (lt) x'
        specific_value_list = [item[key] for item in a]

        i = bisect.bisect_left(specific_value_list, x)
        if i:
            return a[i - 1]
        else:
            return None

    def find_le_by_key(self, a, x, key):
        'Find rightmost item within list of dicts or lists with specific value less than or equal to (le) x'
        specific_value_list = [item[key] for item in a]

        i = bisect.bisect_right(specific_value_list, x)
        if i:
            return a[i - 1]
        else:
            return None

    def find_gt_by_key(self, a, x, key):
        'Find leftmost item within list of dicts or lists with specific value greater than (gt) x'
        specific_value_list = [item[key] for item in a]

        i = bisect.bisect_right(specific_value_list, x)
        if i != len(a):
            return a[i]
        else:
            return None

    def find_ge_by_key(self, a, x, key):
        'Find leftmost item within list of dicts or lists with specific value greater than or equal to (ge) x'
        specific_value_list = [item[key] for item in a]

        i = bisect.bisect_left(specific_value_list, x)
        if i != len(a):
            return a[i]
        else:
            return None

    def get_sublist(self, a, primary_value, primary_value_key, secondary_value=None, secondary_value_key=None):
        """
        Get sublist of items in list sorted by primary value (and secondary value) that satisfy the provided values
        of the primary (and secondary) sorting "factors".
        :param a: sorted list of lists OR list of dicts
        :param primary_value: desired value of primary factor used to sort list
        :param primary_value_key: index or key of primary_value in list or dict
        :param secondary_value: desired value of secondary sorting factor
        :param secondary_value_key: index or key of secondary_value in list or dict
        :return: sublist
        """
        # i) Get list of primary values in list a
        primary_factor_list = [x[primary_value_key] for x in a]

        # ii) Determine beginning and ending indices of sublist satisfying primary_value
        primary_value_left_index = self.index(primary_factor_list, primary_value)

        # ii.a) If primary value not found, return empty list
        if primary_value_left_index is None:
            return []

        # ii.b) Otherwise, get next primary value and right index. If there is no next value, set right index to max.
        next_value = self.find_gt(primary_factor_list, primary_value)
        if next_value is None:
            primary_value_right_index = len(a)
        else:
            primary_value_right_index = self.index(primary_factor_list, next_value)

        # iii) Get sublist of list 'a' satisfying primary value
        sublist_1 = a[primary_value_left_index:primary_value_right_index]
        if secondary_value is None:
            return sublist_1
        else:
            return self.get_sublist(sublist_1, secondary_value, secondary_value_key)
