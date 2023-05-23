import os.path
import streamlit as st
from pandas import DataFrame
from streamlit import session_state as sst

from lib.draw import show_series_cloud
from lib.util import load_side, Crawl

if 'meta' not in sst:
    st.error('Please start from infomation page.')
    st.stop()
meta = sst.meta
load_side()
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


st.sidebar.button('Generate', on_click=show_series_cloud)  # 忽略返回值
