import streamlit as st
from streamlit import session_state as sst

from lib.draw import draw_series_sentiment

if 'meta' not in sst:
    st.error('Please start from infomation page.')
    st.stop()

titles = ('主客观弹幕随剧集分布', '剧集情感值变化曲线', '多维情感弹幕随剧集分布')
tabs = st.tabs(titles)
for tab, fig in zip(tabs, draw_series_sentiment(sst.mid, sst.meta)):
    tab.pyplot(fig)
