import streamlit as st

from lib.draw import st_draw_sentiment
from lib.util import load_side, load_episode
from series.info import meta

with st.sidebar:
    ep_num, disable_history, dt = load_side()
    gen = st.button('Generate')

if disable_history:
    csv_file = f'series\\three\\{ep_num}.csv'
else:
    date_str = dt.strftime('%Y-%m-%d')
    csv_file = f'series\\three\\{ep_num}_{date_str}.csv'

cid = load_episode(meta, ep_num)['cid']
duration = load_episode(meta, ep_num)['duration']
# df = Crawl.crawl_save(csv_file, cid)
if gen:
    st.header('一、主客观弹幕分布饼图')
    st.pyplot(st_draw_sentiment(csv_file, 1,,)

    st.header('二、多维情感分布雷达图')
    st.pyplot(st_draw_sentiment(csv_file, 2,,)

    st.header('三、主客观弹幕在不同时间段的绝对分布情况')
    st.pyplot(st_draw_sentiment(csv_file, 3, cid, duration))
    #
    st.header('四、主客观弹幕在不同时间段的相对分布情况')
    st.pyplot(st_draw_sentiment(csv_file, 4, cid, duration))
    #
    st.header('五、模拟视频热度曲线')
    st.pyplot(st_draw_sentiment(csv_file, 5, cid, duration))
