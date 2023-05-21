import streamlit as st

from lib.db import query_danmaku_by_date
from lib.draw import draw_wordcloud, show_side

# 莫名其妙二人转
if 'mode' in st.session_state:
    st.session_state.new_mode = st.session_state.mode
else:
    st.session_state.mode = st.session_state.new_mode
if 'meta' not in st.session_state:
    st.error('Please start from infomation page.')
    st.stop()


@st.cache_data
def st_draw_hist(date: str):
    metadata = st.session_state.meta
    cid = metadata['cid']
    dmks = query_danmaku_by_date(cid, date)
    if len(dmks) == 0:
        st.error('这一天没有任何弹幕记录。')
        st.stop()
    # dmks = dm_history(cid, date)
    return draw_wordcloud(dmks)


show_side()
