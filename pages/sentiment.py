import streamlit as st
from streamlit import session_state as sst
from lib.db import DBUtil
from lib.draw import *
# todo 加上user先，或考虑把用户分析全部接入单视频

sst.debug = True

if 'mode' in sst:
    sst.new_mode = sst.mode
else:
    sst.mode = sst.new_mode

if 'meta' not in sst:
    st.error('Please start from infomation page.')
    st.stop()

metadata = sst.meta

if sst.mode == 'Single':
    cid = metadata['cid']
    if metadata['duration'] % 1000 == 0:
        duration = metadata['duration'] // 1000
    else:
        duration = metadata['duration']

    dfm = DBUtil.get_all_danmaku2df(cid)
    titles = ('主客观弹幕分布饼图', '多维情感分布雷达图', '视频热度曲线',
              '主客观弹幕在不同时间段的分布', '多维情感弹幕在不同时间段的分布',
              '主客观弹幕在不同日期的分布', '多维情感弹幕在不同日期的分布')
    tabs = st.tabs(titles)
    render_methods = ['plotly_chart'] * 3 + ['pyplot'] * 2
    draw_methods = ['draw_pie', 'draw_multi_radar_graph', 'draw_heat_curve',
                    'draw_stacked_bars_graph', 'draw_multi_curve']

    with st.sidebar:
        intervals: int = st.slider('输入时间段数：', min_value=10, max_value=20)
        date_samples: int = st.slider('输入日期采样数：', min_value=10, max_value=20)

    for i in range(len(draw_methods)):
        # st.header(titles[i])
        if draw_methods[i] in globals():
            figure = globals()[draw_methods[i]](dfm=dfm,
                                                duration=duration,
                                                intervals=intervals)
        else:
            st.error('Method not imported.')
            st.stop()
        # figure = eval(draw_methods[i] + params[i])
        getattr(tabs[i], render_methods[i])(figure)

    # todo 加入了粒度（时间间隔，日期间隔）调节
    # todo 考虑加入热度随日期的分布，需去重以反映该日弹幕情况
    tabs[-2].pyplot(draw_history_bars(sst.vid, cid, date_samples))
    tabs[-1].pyplot(draw_multi_history_bars(sst.vid, cid, date_samples))
elif sst.mode == 'Series':
    titles = ('主客观弹幕随剧集分布', '剧集情感值变化曲线', '多维情感弹幕随剧集分布')
    tabs = st.tabs(titles)
    for tab, fig in zip(tabs, draw_series_sentiment(sst.mid)):
        tab.pyplot(fig)
