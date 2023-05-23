import re

import requests
import streamlit as st
from streamlit import session_state as sst
from streamlit_profiler import Profiler

from lib.db import query_video, upd_video, add_video, query_series
from lib.info import types, avbvid_pattern
from lib.util import auto_wrap, get_up_info, store_sessssion_state, show_tags, rearrange_stat, show_top3_comments, \
    get_metadata, extract_meta

table = 'fZodR9XQDSUm21yCkr6zBqiveYah8bt4xsWpHnJE7jL5VG3guMTKNPAwcF'
tr = {}
for idx in range(58):
    tr[table[idx]] = idx
s = [11, 10, 3, 8, 4, 6]
xor = 177451812
add = 8728348608


def av2bv(aid: int):
    # https://www.zhihu.com/question/381784377/answer/1099438784
    x = (aid ^ xor) + add
    r = list('BV1  4 1 7  ')
    for i in range(6):
        r[s[i]] = table[x // 58 ** i % 58]
    return ''.join(r)


def bv2av(bvid: str):
    r = 0
    for i in range(6):
        r += tr[bvid[s[i]]] * 58 ** i
    return (r - add) ^ xor


def get_cid(url, all_cid=False):
    """

    :param url:
    :param all_cid:
    :return:
    """
    data, p = get_metadata(url)
    cids = {row["page"]: (row['part'], row["cid"]) for row in data["pages"]}
    if all_cid:
        return cids
    elif p == 0:
        return data["cid"]
    else:
        return cids[p]


def get_season_cids(sid):
    url = 'https://api.bilibili.com/pgc/web/season/section?season_id=' + str(sid)
    data: dict = requests.get(url).json()
    return [x.get('cid') for x in data.get('result').get('main_section').get('episodes')]


def get_sid_cid(url: str):
    """

    :param url:
    :return: 2-dimen tuple
    """
    if 'bilibili.com' not in url:
        return
    if avbvid_pattern.search(url):
        return 'cid', get_cid(url)[-1]  # 只返回cid，不返回标题
    if match := re.search(r'/ep(\d+)(?=\?)', url):
        return 'sid', match.group(1)  # sid
    return


@st.cache_data
def get_season_meta(url: str):
    """

    :param url: like https://www.bilibili.com/bangumi/media/mdxxxxxxx
    :return:
    """
    match = re.search(r'(?<=md)\d+', url)
    if match is None:
        return
    mid: str = match.group(0)
    sid_url = 'https://api.bilibili.com/pgc/review/user'
    resp = requests.get(sid_url, params={'media_id': mid}).json()
    sid = resp['result']['media']['season_id']
    # t = get_sid_cid(url)
    # if t is None:
    #     return
    # identifier, sid = t
    # if identifier != 'sid':
    #     return
    # 蓦然回首，一个万金油api全搞定
    final_url = 'https://api.bilibili.com/pgc/view/web/season'
    final_dict = requests.get(final_url, params={'season_id': sid}).json()
    return final_dict['result']


if __name__ == '__main__':
    d = get_season_meta('https://www.bilibili.com/bangumi/media/md787')
    first_url = "https://www.bilibili.com/video/BV1BD4y1u7pN?spm_id_from=333.999.0.0"
    title, cid = get_cid(first_url)
    print(title, cid)


@st.cache_data
def get_raw(img_url):
    return requests.get(img_url).content


def show_series_meta():
    series_input = st.session_state.url
    search = re.search(r'(?<=/md)\d+', series_input)
    if search:
        mid = int(search.group(0))
        series_data = query_series(mid)
        # 有数据且不刷新
        if series_data:
            if st.session_state.flush:
                series_data = get_season_meta(series_input)
                series_data = extract_series(series_data)
                from lib.db import upd_series
                upd_series(mid, **series_data)
            else:
                pass
        else:
            series_data = get_season_meta(series_input)
            episodes = series_data['episodes']
            # st.write(episodes);st.stop()
            series_data = extract_series(series_data)
            from lib.db import add_series
            add_series(mid, episodes, **series_data)
    else:
        st.error('Invalid url. Please input again.')
        return

    sst.meta = series_data
    sst.mid = mid

    st.title(series_data['season_title'])
    # st.caption('Tags: ' + ' '.join(meta['styles']))
    styles = series_data['styles']
    if type(styles) is str:
        styles = styles.split('#')
    tag_data = [{'tag_name': name} for name in styles]
    show_tags(data=tag_data, show=True)

    trans = {'coins': '总投币', 'danmakus': '总弹幕', 'favorite': '总收藏', 'likes': '总点赞',
             'reply': '总评论', 'share': '总转发', 'views': '总点击量'}
    lft, rt = st.columns(2)
    with lft:
        # todo 保持一致换用metric
        # todo 添加评分信息
        st.subheader('数据统计信息')
        for tag in trans.keys():
            v = series_data[tag]
            if v >= 9999:
                num = str(round(v / 10000, 1)) + '万'
            else:
                num = str(v)
            st.text(trans[tag] + ':' + num)
    with rt:
        image_raw = requests.get(series_data['cover']).content
        st.image(image_raw, use_column_width='always')
    # rearrange_stat(meta['stat'], True)

    st.header('简介')
    st.text(auto_wrap(series_data['evaluate']))

    lft, rt = st.columns(2)
    with lft:
        st.header('分集标题')
        with st.expander('查看分集标题'):
            for title in series_data['titles'].split('\n'):
                st.text(title)
    with rt:
        st.header('演职员表')
        with st.expander('展开演职员表'):
            st.subheader('演员表')
            actors_list = series_data['actors'].split('\n')
            st.text(series_data['actors'])
            st.divider()
            st.subheader('职员表')
            st.text(series_data['staff'])


def extract_series(meta):
    episodes: list[dict] = meta['episodes']
    stat = meta['stat']
    critical_keys = ('actors', 'cover', 'evaluate', 'season_title', 'staff',)
    critical_data = {k: v for k, v in meta.items()
                     if k in critical_keys}
    critical_data['styles'] = '#'.join(meta['styles'])
    critical_data['titles'] = '\n'.join([ep['share_copy'] for ep in episodes])
    critical_data.update(stat)
    del critical_data['favorites']
    return critical_data


def show_user_info():
    uid_pattern = re.compile(r'(?<=space.bilibili.com/)\d+')
    if match := uid_pattern.search(st.session_state.url):
        uid = match.group(0)
    else:
        st.error('Invalid url. Please input again.')
        return
    st.session_state.uid = uid
    from lib.db import query_user
    user_dict = query_user(int(uid))

    if user_dict:
        if st.session_state.flush:
            user_data = get_up_info(uid)
            from lib.db import upd_user
            upd_user(int(uid), **user_data)
        user_data = user_dict
    else:
        user_data = get_up_info(uid)
        from lib.db import add_user
        add_user(int(uid), **user_data)
    sst.meta = user_data

    lft, rt = st.columns([8, 2])
    lft.title(user_data['name'])
    lft.caption(user_data['sign'])
    rt.image(get_raw(user_data['face']))

    tags = ['sex', 'level', 'birthday', 'school', 'fans', 'v_num']
    trans = {
        'sex': '性别',
        'level': '等级',
        'birthday': '生日',
        'school': '学校',
        'fans': '粉丝数',
        'v_num': '视频数'
    }
    cols = st.columns(len(tags))
    for tag, col in zip(tags, cols):
        content = user_data.get(tag, None)
        if content == '':
            content = None
        col.metric(trans[tag], content, help=str(content))
    # with lft:
    #     for tag in data:
    #         if tag not in ('name', 'title', 'desc', 'pic', 'face'):
    #             if len(data[tag]) == 0:
    #                 continue
    #             joined = ':'.join((tag.capitalize(), data[tag]))
    #             joined = auto_wrap(joined, 2)
    #             st.text(joined)
    # with rt:
    #     st.image(get_raw(data['face']))

    st.header('代表作')
    most_bvid = user_data.get('most_bvid', None)
    if most_bvid:
        most_meta = query_video(bvid=most_bvid)
        if not most_meta:  # todo 持久化
            most_meta = get_metadata(most_bvid)[0]
        st.subheader(most_meta.get('title', None))
        lft, rt = st.columns(2)
        with lft:
            st.text(auto_wrap(most_meta.get('desc', ''), 2))
        with rt:
            pic = most_meta.get('pic', '')
            if pic:
                st.image(get_raw(pic))


def show_video_meta():
    with Profiler():
        if len(st.session_state.url) == 0:
            return
        tup = get_metadata(st.session_state.url)
        if tup is None:
            st.error('Invalid url. Please input again.')
        else:
            metadata, _ = tup
            store_sessssion_state(metadata, st.session_state.url)
            extracted = extract_meta(metadata)

            st.title(extracted['title'])
            video_dict = query_video(extracted['cid'])
            if video_dict:  # todo 使用字典解包
                if st.session_state.flush:
                    upd_video(**extracted)
                else:
                    extracted = video_dict
            else:
                # tags = show_tags(aid, cid)
                add_video(**extracted)

            st.divider()
            image_raw = get_raw(extracted['pic'])
            st.image(image_raw, caption='视频封面')

            if 'stat' not in extracted:
                stat = {k: v for k, v in extracted.items()
                        if k in types}
            else:
                stat = extracted['stat']
            rearrange_stat(stat, True)
            st.divider()
            st.header('视频简介')

            st.text(extracted['desc'])
            show_top3_comments(extracted['aid'])
