from datetime import datetime
from streamlit import session_state as sst
import streamlit as st

from lib.db import query_video, get_series_total
from lib.draw import show_cloud, show_series_cloud, show_user_cloud
from lib.util import get_date_range

sst.debug = True

if 'mode' in sst:
    sst.new_mode = sst.mode
else:
    sst.mode = sst.new_mode

if 'meta' not in sst:
    st.error('Please start from infomation page.')
    st.stop()

# show_side()
metadata: dict = sst.meta
mode = sst.mode

with st.sidebar:
    # st.checkbox('DEBUG', key='debug', help='开启后不记录弹幕用户信息')
    if mode == 'Series':
        mid = sst.mid
        total = get_series_total(mid)

        show_all = st.checkbox(
            '显示全剧集词云', key='all',
            # 注意这参数只改变label的可见性
            # label_visibility='collapsed' if mode != 'Series' else 'visible'
        )
        ep: int = st.number_input(
            '请输入集数', 1, total,
            disabled=show_all, key='episode',
        )
    if mode != 'User':
        disable_history = st.checkbox('Disable history danmaku',
                                      value=True,
                                      key='disable_history')

    if mode == 'Single':
        show_func = show_cloud
        vid = sst.vid
    elif mode == 'Series':
        show_func = show_series_cloud
        vid_dict = query_video(mid=mid, seq=ep)
        vid = vid_dict['bvid']
        sst.bvid = vid
        sst.cid = vid_dict['cid']
    else:  # USER
        disable_history = True
        show_func = show_user_cloud
        st.checkbox('DEBUG', key='debug', value=True)
        # st.slider('选取视频数量', min_value=1,
        #           max_value=metadata['v_num'], key='v_num',
        #           )
    # 这时再获取日期
    if not disable_history:
        with st.spinner('正在查询历史弹幕日期范围...'):
            date_range = get_date_range(vid)
            sst.latest_date = datetime.strptime(date_range[-1], '%Y-%m-%d')
            sst.earliest_date = datetime.strptime(date_range[0], '%Y-%m-%d')
        st.date_input('Back to:', value=sst.latest_date,
                      key='date', disabled=disable_history,
                      min_value=sst.earliest_date,
                      max_value=sst.latest_date,
                      )
    st.button('Generate', on_click=show_func)
