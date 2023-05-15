import os.path
import streamlit as st
from pandas import DataFrame
from streamlit import session_state as sst

from lib.draw import st_draw_wordcloud, draw_wordcloud
from lib.util import load_side, Crawl

if 'meta' not in sst:
    st.error('Please start from infomation page.')
    st.stop()
meta = sst.meta
load_side(meta)
mid = sst.mid
ep_num = sst.episode
dmk_dir = os.path.join("series", str(mid))
if not os.path.exists(dmk_dir):
    os.mkdir(dmk_dir)


# WORKING DIRECTORY C:\Users\zihao\PycharmProjects\bilipy
def load_series(suffix: str = '') -> list:
    episodes: list[dict] = meta['episodes']
    all_text = []
    for ep in range(0, meta['total']):
        suffix_dir = os.path.join(dmk_dir, suffix)
        if not os.path.exists(suffix_dir):
            os.mkdir(suffix_dir)
        dtf: DataFrame = Crawl.crawl_save(
            os.path.join(dmk_dir, suffix, f'{ep + 1}.csv'),
            episodes[ep]['cid'])
        all_text.extend(dtf['text'].tolist())
    return all_text


def show_cloud():
    with st.spinner('正在生成弹幕词云...'):
        if sst.all:  # 全剧集词云
            if sst.dis_hist:  # 禁历史
                text = load_series()
            else:
                text = load_series(sst.date.strftime('%Y-%m-%d'))
            figure = draw_wordcloud(text)
        else:  # 单集词云
            current_ep: dict = meta['episodes'][ep_num - 1]
            cid = current_ep['cid']
            if sst.dis_hist:
                figure = st_draw_wordcloud(os.path.join(dmk_dir, f'{ep_num}.csv'), cid)
            else:
                date_str = sst.date.strftime('%Y-%m-%d')
                figure = st_draw_wordcloud(os.path.join(dmk_dir, f'{ep_num}_{date_str}.csv'), cid)
        st.pyplot(figure)


st.sidebar.button('Generate', on_click=show_cloud)  # 忽略返回值
