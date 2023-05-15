import re
import requests
import streamlit as st

headers = {
    "authority": "api.bilibili.com",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
    "accept": "application/json, text/plain, */*",
}
avbvid_pattern = re.compile(r'(AV|av|BV|bv)\w+')
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


def get_real_url(url):
    r = requests.head(url, headers=headers)
    return r.headers['Location']


def get_avbvid(url):
    if "b23.tv" in url:
        url = get_real_url(url)
    try:
        avbvid = avbvid_pattern.search(url).group(0)
    except AttributeError:
        return

    url = url.strip("/")
    m_obj = re.search(r"[?&]p=(\d+)", url)
    p = 0
    if m_obj:
        p = int(m_obj.group(1))
    # s_pos = url.rfind("/") + 1
    # r_pos = url.rfind("?")
    # avbvid = None
    # if r_pos == -1:
    #     avbvid = url[s_pos:]
    # else:
    #     avbvid = url[s_pos:r_pos]
    if avbvid.startswith("av") or avbvid.startswith('AV'):
        return "aid", avbvid[2:], p
    elif avbvid.startswith("bv") or avbvid.startswith('BV'):
        return "bvid", avbvid, p


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


@st.cache_data
def get_metadata(url):
    """

    :param url: B站单个视频的链接
    :return: metadata, 分p（不分p返回0）
    链接无法识别时，返回None
    """
    tup = get_avbvid(url)
    if tup is None:
        return
    typ, avbvid, p = tup
    res = requests.get(
        f"https://api.bilibili.com/x/web-interface/view?{typ}={avbvid}", headers=headers)
    res.encoding = "u8"
    data: dict = res.json()['data']
    return data, p


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
    first_url = "https://www.bilibili.com/video/BV1BD4y1u7pN?spm_id_from=333.999.0.0"
    title, cid = get_cid(first_url)
    print(title, cid)


@st.cache_data
def get_raw(img_url):
    return requests.get(img_url).content
