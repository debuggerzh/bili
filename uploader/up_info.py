import re
import streamlit as st

from lib.meta import get_raw
from lib.util import auto_wrap, get_up_info


def show_info(refresh: bool):
    uid_pattern = re.compile(r'(?<=space.bilibili.com/)\d+')
    if match := uid_pattern.search(space_url):
        uid = match.group(0)
    else:
        st.error('Invalid url. Please input again.')
        return
    st.session_state.uid = uid
    user_data = get_up_info(uid)
    from lib.db import query_user
    user_dict = query_user(int(uid))
    if user_dict:
        if refresh:
            from lib.db import upd_user
            upd_user(int(uid), **user_data)
        else:
            pass    # todo
    else:
        from lib.db import add_user
        add_user(int(uid), **user_data)
    lft, rt = st.columns([8, 2])
    lft.title(user_data['name'])
    lft.caption(user_data['sign'])
    rt.image(get_raw(user_data['face']))

    tags = ['sex', 'level', 'birthday', 'school', 'fans', 'v_num']
    trans = {
        'sex': '性别',
        'level': '等级',
        'birthday': '生日',
        'school': '学校',
        'fans': '粉丝数',
        'v_num': '视频数'
    }
    cols = st.columns(len(tags))
    for tag, col in zip(tags, cols):
        col.metric(trans[tag], user_data[tag])
    # with lft:
    #     for tag in data:
    #         if tag not in ('name', 'title', 'desc', 'pic', 'face'):
    #             if len(data[tag]) == 0:
    #                 continue
    #             joined = ':'.join((tag.capitalize(), data[tag]))
    #             joined = auto_wrap(joined, 2)
    #             st.text(joined)
    # with rt:
    #     st.image(get_raw(data['face']))

    st.header('代表作')
    st.subheader(user_data['title'])
    lft, rt = st.columns(2)
    with lft:
        st.text(auto_wrap(user_data['desc'], 2))
    with rt:
        st.image(get_raw(user_data['pic']))


with st.sidebar:
    space_url = st.text_input('Please input space url of the uploader:',
                              help='Example: https://space.bilibili.com/108618052')
    flush = st.checkbox('Force flush database', key='flush')
    gen = st.button('Generate', on_click=show_info, args=(st.session_state.flush,))
