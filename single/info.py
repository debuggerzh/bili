import sys

import streamlit as st

from lib.db import add_video, query_video, upd_video
from lib.meta import get_metadata, get_raw
from lib.util import *

types = ('view', 'danmaku', 'like', 'coin', 'favorite', 'share', 'reply')
if sys.platform.startswith('linux'):
    sys.path.append('/app/bili')

# todo 合三为一！

def show_meta(refresh: bool):
    if len(vid_url) == 0:
        return
    tup = get_metadata(vid_url)
    if tup is None:
        st.error('Invalid url. Please input again.')
    else:
        metadata, _ = tup
        store_sessssion_state(metadata, vid_url)
        cid = metadata['cid']
        bvid = metadata['bvid'].lower()
        title = metadata['title']
        aid = metadata['aid']
        img_url = metadata['pic']
        stat = metadata['stat']
        wrapped = auto_wrap(metadata['desc'])

        st.title(title)
        tags = show_tags(aid, cid, show=True)
        video_dict = query_video(cid)
        if video_dict:
            if refresh:
                upd_video(cid, pic=img_url, tags=tags, title=title, desc=wrapped,
                          view=stat['view'], danmaku=stat['danmaku'], reply=stat['reply'],
                          favorite=stat['favorite'], coin=stat['coin'], share=stat['share'],
                          like=stat['like'])
            else:
                video_dict['bvid']
                aid = video_dict['aid']
                img_url = video_dict['pic']
                stat = {k: v for k, v in video_dict.items() if k in types}
                # tag_data = [{'tag_name': name} for name in video_dict['tags'].split('#')]
                # show_tags(data=tag_data, show=True)
                wrapped = video_dict['desc']
        else:
            # tags = show_tags(aid, cid)
            add_video(pic=img_url, tags=tags, title=title, bvid=bvid, cid=cid, aid=aid,
                      desc=wrapped,
                      view=stat['view'], danmaku=stat['danmaku'], reply=stat['reply'],
                      favorite=stat['favorite'], coin=stat['coin'], share=stat['share'],
                      like=stat['like']
                      )

        # dbutil = DBUtil(
        #     pic=img_url, tags=tags, title=title, bvid=bvid, cid=cid, aid=aid,
        #     desc=wrapped,
        #     # 以下为统计数据
        #     view=stat['view'], danmaku=stat['danmaku'], reply=stat['reply'],
        #     favorite=stat['favorite'], coin=stat['coin'], share=stat['share'],
        #     like=stat['like']
        # )
        # st.session_state.dbutil = dbutil
        st.divider()

        # lft, rt = st.columns([0, 9])
        # with lft:
        #     pass
        #     # st.metric('UP主', metadata['owner']['name'])
        #     # st.image(get_raw(metadata['owner']['face']))
        # with rt:

        image_raw = get_raw(img_url)
        st.image(image_raw, caption='视频封面')

        rearrange_stat(stat, True)
        st.divider()
        st.header('视频简介')

        st.text(wrapped)
        show_top3_comments(aid)


with st.sidebar:
    st.session_state.flush = False
    vid_url = st.text_input('Please input video url:', key='vid_url',
                            on_change=show_meta, args=(st.session_state.flush,))
    flush = st.checkbox('Force flush database', key='flush')
    start = st.button('Start', on_click=show_meta, args=(st.session_state.flush,))
# def show_hot_danmakus(danmakus_csv: str, cid: int):
#     df = Crawl.crawl_save(danmakus_csv.format(cid), cid, _need_likes=False)
#     st.header('热门弹幕')
#     selected: DataFrame = df[['text', 'likes']].head()
#     st.table(selected)

# todo 考虑把弹幕赞数加入词云及情感分析，加权
# vid_url = r'https://www.bilibili.com/video/BV1ms4y117ow'  学习区:11
# https://www.bilibili.com/video/BV1t34y157sn/  虚拟区:247
# https://www.bilibili.com/video/BV1i44y167KL/? 体育：991
