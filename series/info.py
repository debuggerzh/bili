import requests
import streamlit as st
from streamlit import session_state as sst

from lib.meta import get_season_meta
from lib.util import auto_wrap, rearrange_stat


def show_meta():
    if len(series_input) == 0:
        return
    meta = get_season_meta(series_input)
    if meta is None:
        st.error('Invalid url. Please input again.')
        return
    sst.meta = meta
    sst.mid = meta['media_id']

    st.title(meta['title'])
    st.caption('Tags: ' + ' '.join(meta['styles']))
    trans = {'coins': '总投币', 'danmakus': '总弹幕', 'favorite': '总收藏', 'likes': '总点赞',
             'reply': '总评论', 'share': '总转发', 'views': '总点击量'}
    lft, rt = st.columns(2)
    with lft:
        st.subheader('数据统计信息')
        for tag, v in meta['stat'].items():
            if tag == 'favorites':
                continue
            if v >= 9999:
                num = str(round(v / 10000, 1)) + '万'
            else:
                num = str(v)
            st.text(trans[tag] + ':' + num)
    with rt:
        image_raw = requests.get(meta['cover']).content
        st.image(image_raw)
    # rearrange_stat(meta['stat'], True)

    st.header('简介')
    st.text(auto_wrap(meta['evaluate']))
    episodes: list[dict] = meta['episodes']
    lft, rt = st.columns(2)
    with lft:
        st.header('分集标题')
        with st.expander('查看分集标题'):
            for ep in episodes:
                st.text(ep['share_copy'])
    with rt:
        st.header('演职员表')
        with st.expander('展开演职员表'):
            st.subheader('演员表')
            actors_list = meta['actors'].split('\n')
            st.text(meta['actors'])
            st.divider()
            st.subheader('职员表')
            st.text(meta['staff'])


with st.sidebar:
    series_input = st.text_input('请输入剧集链接',
                                 help='https://www.bilibili.com/bangumi/media/mdxxx',
                                 autocomplete='url',
                                 on_change=show_meta)
    start = st.button('Start', on_click=show_meta)
# series_url = r'https://www.bilibili.com/bangumi/media/md28229055'
# 另一个是夏色奇迹
