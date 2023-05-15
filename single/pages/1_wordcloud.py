import os.path
from datetime import datetime
import pandas as pd
import streamlit as st
from pandas import DataFrame

from lib.db import get_all_danmaku_text, DBUtil, query_danmaku_by_date
from lib.draw import draw_wordcloud
from lib.util import get_date_range, dm_history, convert_df

if 'meta' not in st.session_state:
    st.error('Please start from infomation page.')
    st.stop()
metadata = st.session_state.meta
cid = metadata['cid']


# dbutil: DBUtil = st.session_state.dbutil


@st.cache_data
def st_draw_hist(date: str):
    cid, date
    dmks = query_danmaku_by_date(cid, date)
    if len(dmks) == 0:
        st.error('这一天没有任何弹幕记录。')
        st.stop()
    # dmks = dm_history(cid, date)
    return draw_wordcloud(dmks)


def show_cloud():
    with st.spinner('正在生成弹幕词云...'):
        if disable_history:  # 全弹幕
            dmks = get_all_danmaku_text(cid)
            fig = draw_wordcloud(dmks)
            # fig = st_draw_wordcloud(st.session_state.csv, metadata['cid'])
            st.pyplot(fig)
            with st.spinner('正在准备下载...'):
                df = DBUtil.get_all2df(cid)
                st.info('请使用UTF-8编码打开')
                # df: DataFrame = Crawl.crawl_save(st.session_state.csv, metadata['cid'])
                st.download_button('Download danmaku file',
                                   convert_df(df),
                                   os.path.basename(st.session_state.csv),
                                   on_click=lambda: st.info('请使用UTF-8编码打开'),
                                   mime='text/csv')
        else:
            strftime = dt.strftime('%Y-%m-%d')
            st.pyplot(st_draw_hist(strftime))
            hist_file_path = os.path.join(os.path.dirname(st.session_state.csv),
                                          f'{cid}_{strftime}.csv')
            df: DataFrame = DBUtil.get_all2df_by_date(cid, strftime)
            st.download_button('Download danmaku file',
                               convert_df(df),
                               os.path.basename(hist_file_path),
                               mime='text/csv')


with st.spinner('正在查询历史弹幕日期范围...'):
    date_range = get_date_range(st.session_state.vid)
    latest_date = datetime.strptime(date_range[-1], '%Y-%m-%d')

with st.sidebar:
    disable_history = st.checkbox('Disable history danmaku', key='disabled')
    dt: datetime.date = st.date_input('Back to:', value=latest_date, key='dt',
                                      min_value=datetime.strptime(date_range[0], '%Y-%m-%d'),
                                      max_value=latest_date,
                                      disabled=st.session_state.disabled,
                                      )
    gen = st.button('Generate', on_click=show_cloud)
