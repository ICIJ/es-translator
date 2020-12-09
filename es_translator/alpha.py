from pycountry import languages

def to_alpha_2(code):
    if len(code) == 3:
        return languages.get(alpha_3 = code).alpha_2
    else:
        return code

def to_alpha_3(code):
    if len(code) == 2:
        return languages.get(alpha_2 = code).alpha_3
    else:
        return code

def to_name(alpha_2):
    return languages.get(alpha_2=alpha_2).name

def to_alpha_3_pair( pair):
    [source, target] = pair.split('-')
    return '%s-%s' % (to_alpha_3(source), to_alpha_3(target))
