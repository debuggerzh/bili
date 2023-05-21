import streamlit as st
from streamlit_profiler import Profiler

from lib.meta import show_series_meta, show_user_info, show_video_meta

# todo 合三为一！

with st.sidebar:
    mode = st.radio('Select mode:', ('Single', 'Series', 'User'), key='mode')
    st.session_state.mode
    if mode == 'Single':
        input_text = '请输入视频链接：'
        help_text = 'https://www.bilibili.com/video/BVxxxxxxxx'
        show_func = show_video_meta
    elif mode == 'Series':
        input_text = '请输入剧集链接：'
        help_text = 'https://www.bilibili.com/bangumi/media/mdxxx'
        show_func = show_series_meta
    else:
        input_text = '请输入UP主空间链接：'
        help_text = 'https://space.bilibili.com/108618052'
        show_func = show_user_info
    st.text_input(input_text, key='url', help=help_text,
                  autocomplete='url', )
    st.checkbox('Force flush database', key='flush')
    st.button('Start', on_click=show_func)

# def show_hot_danmakus(danmakus_csv: str, cid: int):
#     df = Crawl.crawl_save(danmakus_csv.format(cid), cid, _need_likes=False)
#     st.header('热门弹幕')
#     selected: DataFrame = df[['text', 'likes']].head()
#     st.table(selected)

# todo 考虑把弹幕赞数加入词云及情感分析，加权
# vid_url = r'https://www.bilibili.com/video/BV1ms4y117ow'  学习区:11
# https://www.bilibili.com/video/BV1t34y157sn/  虚拟区:247
# https://www.bilibili.com/video/BV1i44y167KL/? 体育：991

# series_url = r'https://www.bilibili.com/bangumi/media/md28229055'
# https://www.bilibili.com/bangumi/media/md787

# https://space.bilibili.com/108618052
