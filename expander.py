from copy import copy


def expand_dict(basedict, fix_dict = {}, level=1):
    """ Flattens a dictionary for the 'variable' entry of a config YAML file.
    """
    if len(basedict) == 0:
        return [{}]

    # First peel off the outer dictionary.
    curlevel = [{k : v} for k, v in basedict.items() if v['order'] == level]
    if len(curlevel) != 1:
        raise ValueError('duplicate or missing order.')
    else:
        name, curdict = list(curlevel[0].items())[0]
        newbase = copy(basedict)
        del newbase[name]

    all_dicts = []
    for val in curdict['values']:
        fd = copy(fix_dict)
        fd[name] = val
        for m in expand_dict(newbase, fix_dict=fd, level=level+1):
            all_dicts.append(copy(fd))
            all_dicts[-1].update(m)
    return all_dicts
