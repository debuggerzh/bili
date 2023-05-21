import streamlit as st

from lib.meta import show_series_meta

with st.sidebar:
    series_input = st.text_input('请输入剧集链接',
                                 help='https://www.bilibili.com/bangumi/media/mdxxx',
                                 autocomplete='url',
                                 key='url',
                                 )
    st.button('Start', on_click=show_series_meta)
# series_url = r'https://www.bilibili.com/bangumi/media/md28229055'
# https://www.bilibili.com/bangumi/media/md787 夏色奇迹
# todo 接入数据库
