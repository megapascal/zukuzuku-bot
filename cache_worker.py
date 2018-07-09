# coding: utf8

import cache_file



def translation_search_in_cache(txt, end_lang):
    res = {
        'result': False,
        'text': ''
    }
    try:
        res['text'] = cache_file.translations[end_lang][txt]
        res['result'] = True
    except Exception:
        pass
        print('used translation cache')

    return res
    
def translation_add_to_cache(source, txt, end_lang):
    cache_file.translations[end_lang][source] = txt
    
def group_info_search_in_cache(group_id):
    res = {
        'result': False,
        'text': ''
    }
    try:
        res['text'] = cache_file.group_info[group_id]
        res['result'] = True
        print('used group info cache')
    except Exception:
        pass
    return res
    
def group_info_update_cache(group_id, params):
    cache_file.group_info[group_id] = params