import csv
import json
import os.path
import random
import re
from datetime import datetime
from pprint import pprint

import requests
import pandas as pd
from bs4 import BeautifulSoup as BS
from google.protobuf.json_format import MessageToJson
from requests import RequestException
import streamlit as st
from retrying import retry

from lib.dm_pb2 import DmSegMobileReply
from lib.info import date_headers, critical_cookie, user_headers, kuai_proxies, avbvid_pattern, types

__all__ = ['auto_wrap', 'show_tags', 'show_top3_comments', 'store_sessssion_state',
           'rearrange_stat', 'Crawl']


def retry_if_error(exception):
    err_classes = (KeyError, AttributeError, TypeError)
    for cls in err_classes:
        if isinstance(exception, cls):
            return True
    return False


class Crawl:
    @staticmethod
    @st.cache_data
    def crawl_save(dest_file: str, cid: int, _need_likes=False):
        """
        允许Ctrl-C中断点赞数爬取
        若已爬取过，直接返回，并在streamlit缓存
        :param _need_likes: 表示需要添加弹幕点赞数一列
        :param dest_file: 要存储的csv文件名
        :param cid:
        :return: 已读取csv的DataFrame，按点赞数和时间降序排列
        """
        if not os.path.exists(dest_file):
            with open(dest_file, mode='w', encoding='utf-8', newline='') as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(['time', 'text', 'mode', 'size', 'color', 'user', 'dmid'])
                soup = Crawl.get_danmakus_from_xml(cid, True)
                for danmaku in soup.find_all('d'):
                    properties = danmaku['p'].split(',')
                    dm_time = properties[0]
                    mode = properties[1]  # 8代表高级弹幕
                    size = properties[2]  # 25为默认值
                    color = properties[3]  # 十进制
                    user = properties[-3]  # 十六进制，这里B站做了调整，在最后增加了weight参数
                    dmtext = danmaku.text
                    dmid = properties[-2]  # 弹幕ID
                    writer.writerow((dm_time, dmtext, mode, size, color, user, dmid))
        df = pd.read_csv(dest_file)

        try:
            if _need_likes:
                if 'likes' not in df.columns:
                    df['likes'] = list(map(Crawl.get_dm_likes, (cid,) * len(df), df['dmid']))
        except KeyboardInterrupt:
            df['likes'] = (0,) * len(df)
        finally:
            if 'likes' not in df.columns:
                df['likes'] = (0,) * len(df)
            df.to_csv(dest_file, index=False)
            return df.sort_values(["likes", "time"], ascending=False, inplace=False)

    @staticmethod
    def get_danmakus_from_xml(cid, raw=False):
        """

        :param cid:
        :param raw: True则返回BeautifulSoup对象
        :return:
        """
        url = f'https://comment.bilibili.com/{cid}.xml'
        resp = requests.get(url).content.decode()
        soup = BS(resp, 'xml')
        if raw:
            return soup
        danmakus = [x.text for x in soup.find_all('d')]
        separated = '\n'.join(danmakus)
        return separated

    @staticmethod
    @retry(retry_on_exception=retry_if_error)
    def get_space_info(uid: int):
        err_code = (-401, -404)
        try:
            base_url = 'https://api.bilibili.com/x/space/wbi/acc/info'
            remain = ('name', 'sex', 'face', 'sign', 'level', 'birthday')
            from lib.info import user_headers
            resp = requests.get(base_url, params={'mid': uid}, headers=user_headers,
                                cookies=critical_cookie)
            resp_json = resp.json()
            if resp_json['code'] in err_code:
                final_dict = dict.fromkeys(remain, '')
                final_dict['school'] = None
                final_dict['level'] = -1  # 表示号寄了
                final_dict['sex'] = 2  # 表示保密
            else:
                data: dict = resp_json['data']
                final_dict = {k: str(v) for k, v in data.items() if k in remain}
                # icon = get_raw(data['face'])
                # todo 目前已知data['school']可能为None，或可能有'name'，或'name'可能为空串
                if 'school' in data and data['school']:
                    if 'name' in data['school']:
                        final_dict['school'] = data['school']['name']
                        if len(final_dict['school']) == 0:
                            final_dict['school'] = None
                    else:
                        final_dict['school'] = None
                else:
                    final_dict['school'] = None
        except (KeyError, AttributeError, TypeError) as e:
            print(uid, type(e), e)
            raise e
        return final_dict

    @staticmethod
    def get_gender(mid: int):
        """

        :param mid:
        :return: 0-Female, 1-Male, -1 means secret or 接口超限
        """
        # time.sleep(1)  # 该接口反扒严重！！！QTMD
        api_url = 'https://api.bilibili.com/x/space/acc/info'
        need_proxy = random.randint(0, 1)
        if need_proxy == 1:
            proxies = kuai_proxies
        else:
            proxies = None
        try:
            resp = requests.get(api_url, params={'mid': mid, 'jsonp': 'jsonp'},
                                cookies=critical_cookie,
                                headers=user_headers,
                                proxies=proxies)
            search = re.search(r'(?<=\"sex\":\")[保密男女]+', resp.text)
            gender = search.group(0)
        except RequestException as e:
            print(e.args)
            return -1
        except AttributeError:
            return -1
        # 因API返回不够严谨，只得用正则进行提取
        # data = resp.json()
        # gender = data['data']['sex']
        if gender == '女':
            return 0
        elif gender == '男':
            return 1
        elif gender == '保密':
            return -1
        print(resp.text)  # 若运行到此，是我不理解的

    @staticmethod
    def get_dm_likes(cid: int, dmid: int):
        """

        :param cid:
        :param dmid:
        :return: 弹幕点赞数，-1表示获取失败
        """
        res = requests.get(
            f"https://api.bilibili.com/x/v2/dm/thumbup/stats?oid={cid}&ids={dmid}", headers=user_headers)
        r = res.json()
        dmid = str(dmid)
        if "data" in r:
            print(r["data"][dmid]["likes"])
            return r["data"][dmid]["likes"]
        else:
            print(r)
            return -1


class Contstant:
    INTERVAL = 60
    POSITIVE = 1
    NEGATIVE = -1
    back_path = os.path.join('resources', 'btv.jpg')
    font_path = os.path.join('resources', 'vista_black.ttf')


class Util:
    import jieba
    emotion_types = ['happy', 'like', 'anger', 'sad', 'surprise', 'disgust', 'fear']
    level_types = {'most': 8, 'very': 6, 'more': 4,
                   'ish': 2, 'insufficient': 0.5, 'inverse': -1}

    all_path = os.path.join('resources', 'dicts', 'jieba_sentiment.txt')
    abbr_path = os.path.join('resources', 'abbr.txt')

    stop_words_path = os.path.join('resources', 'stop.txt')
    positive_words_path = os.path.join('resources', 'dicts', 'positive.txt')
    negative_words_path = os.path.join('resources', 'dicts', 'negative.txt')

    most_words_path = os.path.join('resources', 'dicts', 'most.txt')
    very_words_path = os.path.join('resources', 'dicts', 'very.txt')
    more_words_path = os.path.join('resources', 'dicts', 'more.txt')
    # ish表大约，大概，左右
    ish_words_path = os.path.join('resources', 'dicts', 'ish.txt')
    insufficient_words_path = os.path.join('resources', 'dicts', 'insufficient.txt')
    inverse_words_path = os.path.join('resources', 'dicts', 'inverse.txt')

    paths = [stop_words_path, positive_words_path, negative_words_path,
             most_words_path, very_words_path, more_words_path, ish_words_path,
             insufficient_words_path, inverse_words_path]

    def __init__(self):
        pattern = r'\w+(?=\.txt)'
        for path in Util.paths:
            with open(path, encoding='utf-8') as f:
                var_name = re.search(pattern, path).group(0)
                setattr(self, var_name + '_words', f.read().splitlines())
        # 词典录入jieba分词
        Util.jieba.load_userdict(Util.all_path)
        Util.jieba.load_userdict(Util.positive_words_path)
        Util.jieba.load_userdict(Util.negative_words_path)

        self.abbr_dict = {}
        with open(Util.abbr_path, encoding='utf-8') as f:
            for line in f.read().splitlines():
                k, v = line.split(':')
                self.abbr_dict[k] = v

        df = pd.read_csv(os.path.join('resources', 'dicts/multi_dimen.csv'))
        for emotion in Util.emotion_types:
            setattr(self, emotion + '_words', df[df['type'] == emotion]['word'].tolist())

    def match_adverb(self, word):
        for lev, val in Util.level_types.items():
            if word in getattr(self, lev + '_words'):
                return val
        return 1

    def match_multi(self, word):
        for emotion in Util.emotion_types:
            if word in getattr(self, emotion + '_words'):
                return emotion

    def expand(self, sentence: str):
        for pattern, whole in self.abbr_dict.items():
            sentence = re.sub(pattern, whole, sentence, flags=re.I)
        return sentence


util = Util()


@st.cache_data
def get_date_range(vid: str):
    """

    :return:
    """
    meta = get_metadata(vid)[0]
    month_url = 'https://api.bilibili.com/x/v2/dm/history/index?type=1&oid={}&month={}'
    # date_url = 'https://api.bilibili.com/x/v2/dm/history?type=1&oid={}&date={}'
    # title, cid = get_cid(vid_url)
    # data = get_metadata(url)[0]
    cid = meta['cid']
    pubdate = meta['pubdate'] if 'pubdate' in meta else meta['pub_time']
    start_month = datetime.fromtimestamp(pubdate).strftime('%Y-%m')
    month_range = pd.date_range(start_month, datetime.today(),  # MS:month start frequency
                                freq='MS').strftime("%Y-%m").tolist()
    days: list[str] = []
    for month in month_range:
        response = requests.get(url=month_url.format(cid, month), headers=date_headers,
                                cookies=critical_cookie)
        month_data = response.json().get('data')
        # pprint(month_data)
        if month_data:
            days.extend(month_data)
        else:
            st.write(response.text)
    return days


def auto_wrap(s: str, column=1):
    """
    为适应st.text，每一定字数自动换行（插入换行符）
    :param column: 平均分割的分栏数
    :param s: 需要自动换行的文本
    :return: 已自动换行的文本
    """
    if not s:
        return ''
    entire = 50
    part_sentence = s.split('\n')
    cutted = []
    for sentence in part_sentence:
        current_list = re.findall(r'.{%d}' % (entire // column), sentence)
        cutted.extend(current_list)
        remain = sentence[len(current_list) * entire // column:]
        if len(remain) == 0:
            continue
        cutted.append(remain)
    return '\n'.join(cutted)


@st.cache_data
def dm_history(cid: int, date: str):
    """

    :param date: '%Y-%m-%d'
    :type cid: object
    :return: 某天的弹幕列表
    """
    url_history = f'https://api.bilibili.com/x/v2/dm/web/history/seg.so?type=1&oid={cid}&date={date}'
    resp = requests.get(url_history, cookies=critical_cookie)
    dmk = DmSegMobileReply()
    dmk.ParseFromString(resp.content)
    data_dict: dict = json.loads(MessageToJson(dmk))
    # print(data_dict['elems'][0].keys())
    hist_file_path = os.path.join(os.path.dirname(st.session_state.csv),
                                  f'{cid}_{date}.csv')
    with open(hist_file_path, mode='w', encoding='utf-8', newline='') as csv_file:
        writer = csv.writer(csv_file)
        tags = ('mode', 'fontsize', 'color', 'midHash', 'content')
        writer.writerow(tags)
        try:
            for item in data_dict['elems']:
                writer.writerow([item.get(x, '') for x in tags])
        except csv.Error:
            from pprint import pprint
            pprint(item)
    # st.write(data_dict)
    words: list[str] = [x.get('content', '') for x in data_dict.get('elems', [])]
    # list(map(lambda x=None: print(x['content']), data_dict.get('elems', [])))
    '''厌语丁真，评价为十分炫技的写法
    None是x的默认值（事实上取不到），用map把每个elem的content输出
    map返回迭代器，使用list可全部打印'''
    return words


def load_side():
    """

    :param sentiment: True时禁用复选框，从而禁用日期选择
    :return: date为None表示全弹幕
    """
    metadata = st.session_state.meta
    with st.sidebar:
        show_all = st.checkbox('显示全剧集词云', key='all')
        ep: int = st.number_input('请输入集数', 1, metadata['total'], disabled=show_all,
                                  key='episode')
        disable_hist = st.checkbox('禁用历史日期', value=True,
                                   key='dis_hist')
        if not disable_hist:
            date_range = get_date_range(metadata['episodes'][ep - 1]['bvid'])
            latest_date = datetime.strptime(date_range[-1], '%Y-%m-%d')
            st.date_input('Back to:', value=latest_date, key='date',
                          min_value=datetime.strptime(date_range[0], '%Y-%m-%d'),
                          max_value=latest_date,
                          )


@st.cache_data
def load_episode(_meta: dict, ep: int):
    return _meta['episodes'][ep - 1]


@st.cache_data
def get_up_info(uid):
    """

    :param uid:
    :return: 大体全面的用户数据
    """
    final_dict = {}
    final_dict.update(Crawl.get_space_info(uid))
    # 代表作
    most_bvid = get_user_videos(uid)[0]['bvid']
    final_dict['most_bvid'] = most_bvid
    # top_url = 'https://api.bilibili.com/x/space/top/arc'
    # remain = ('title', 'desc', 'pic')
    # try:
    #     resp = requests.get(top_url, params={'vmid': uid}, headers=user_headers)
    #     data = resp.json()['data']
    #     final_dict.update({k: str(v) for k, v in data.items() if k in remain})
    # except AttributeError as e:
    #     print(e)

    relation_url = 'https://api.bilibili.com/x/relation/stat'
    try:
        resp = requests.get(relation_url, params={'vmid': uid}, headers=user_headers)
        data = resp.json()['data']
        final_dict['fans'] = str(data['follower'])
    except AttributeError as e:
        print(e)

    upstat_url = "https://api.bilibili.com/x/space/navnum"
    try:
        resp = requests.get(upstat_url, params={'mid': uid, 'jsonp': 'jsonp'},
                            headers=user_headers)
        data = resp.json()['data']
        v_num = data['video']  # 视频数量
    except (AttributeError, TypeError) as e:
        v_num = 0
        print(e)
    finally:
        final_dict['v_num'] = v_num
    return final_dict


def show_tags(aid: int = None, cid: int = None, data=None, show=False):
    url = 'https://api.bilibili.com/x/web-interface/view/detail/tag'
    from lib.info import user_headers
    if data:
        tag_data = data
    else:
        resp = requests.get(url, {'aid': aid, 'cid': cid}, headers=user_headers)
        tag_data = resp.json()['data']
    tags_len = len(tag_data)
    turns = (tags_len - 1) // 5 + 1
    tags = []
    for i in range(turns):
        columns = st.columns(5)
        for tag, col in zip(tag_data[5 * i:], columns):
            name_ = tag['tag_name']
            if show:
                col.button(name_)
            tags.append(name_)
    return '#'.join(tags)


def show_top3_comments(aid: int):
    url = 'https://api.bilibili.com/x/v2/reply/main'
    params = {'csrf': '4344d9ff5f9a262d325abfb315ea5439',
              'mode': 3,
              'oid': aid,
              'type': 1,
              }
    from lib.info import user_headers
    resp = requests.get(url, params, headers=user_headers).json()
    if 'data' not in resp:
        st.text('无任何评论。')
        return
    replies = resp['data']['replies']
    st.header('评论Top3')
    tot_len = 0
    for i in range(3 if len(replies) > 3 else len(replies)):
        left, right = st.columns((9, 1))
        left.subheader(replies[i]['member']['uname'])
        right.text('👍' + str(replies[i]['like']))
        message = replies[i]['content']['message']
        tot_len += len(message)
        st.text(auto_wrap(message))
    # print(tot_len)


def store_sessssion_state(metadata, vid_url):
    danmakus_csv = r'resources\danmakus\{}.csv'
    cid = metadata['cid']
    st.session_state.csv = danmakus_csv.format(cid)
    st.session_state.meta = metadata
    st.session_state.vid = vid_url


def rearrange_stat(stat, metric=False):
    from lib.info import types
    trans = {'view': '播放量', 'views': '播放量',
             'danmaku': '弹幕数', 'like': '点赞数', 'coin': '投币数', 'favorite': '收藏数',
             'share': '转发数', 'reply': '评论数'}
    if metric:
        cols = st.columns(len(types))
        for tag, col in zip(types, cols):
            if tag == 'view' and tag not in stat:
                stat_value = stat['views']
            else:
                stat_value = stat[tag]
            if stat_value >= 9999:
                num = str(round(stat_value / 10000, 1)) + '万'
            else:
                num = str(stat_value)
            col.metric(trans[tag], num, help=num)
        return

    tbl_data = []
    for tag in types:

        stat_value = stat[tag]
        if stat_value >= 9999:
            num = str(round(stat_value / 10000, 1)) + '万'
        else:
            num = str(stat_value)
        tbl_data.append([trans[tag], num])
    frame = pd.DataFrame(tbl_data, columns=['指标', '数量'])
    return frame


@st.cache_data
def convert_df(df, encoding='utf-8'):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode(encoding)


@retry(retry_on_exception=lambda e: isinstance(e, KeyError))
def get_user_videos(uid):
    search_url = 'https://api.bilibili.com/x/space/arc/search'
    params = {'mid': uid, 'ps': 30, 'tid': 0, 'pn': 1, 'keyword': '',
              'order': 'click'  # 按点击量降序
              }
    resp = requests.get(search_url, params, headers=user_headers, stream=True)
    try:
        data = resp.json()['data']
    except RequestException:
        decoder = json.JSONDecoder()
        text = resp.text
        while text:
            json_data, index = decoder.raw_decode(text)
            text = text[index:].lstrip()
            if 'data' in json_data:
                data = json_data['data']
                break
    videos = data['list']['vlist']
    return videos


def get_avbvid(url):
    if "b23.tv" in url:
        r = requests.head(url, headers=user_headers)
        url = r.headers['Location']
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
        f"https://api.bilibili.com/x/web-interface/view?{typ}={avbvid}",
        headers=user_headers)
    res.encoding = "u8"
    data: dict = res.json()['data']
    return data, p


def extract_meta(metadata):
    video_keys = ('cid', 'bvid', 'title', 'aid', 'pic',)
    extracted = {k: str(v) for k, v in metadata.items()
                 if k in video_keys}
    extracted_stat = {k: v for k, v in metadata['stat'].items()
                      if k in types}
    # extracted.update(extracted_stat)
    extracted['stat'] = extracted_stat
    extracted['desc'] = auto_wrap(metadata['desc'])
    tags = show_tags(extracted['aid'], extracted['cid'], show=False)
    extracted['tag'] = tags
    return extracted


if __name__ == '__main__':
    vid_u = "https://www.bilibili.com/video/BV1XW411F7L6/?vd_source=58a41ac877c965b4616d2d9f764c219d"
    print(get_date_range(vid_u))
    text = '''我真的觉得很恐怖，就是有一个人开盒了我在别的平台看直播的私人账号，然后开小号把这个账号发给了我的老公粉。跟我的老公粉说我背地里在看别的男主播，叫他们不要再喜欢我了不要再给我送礼物了。
我觉得这个事情很恐怖啊，首先，这个人他真的很阴暗，其次，他是出于什么目的、出于什么身份的呢？
他是我的粉丝？还是我的竞争对手？自己没有能力打倒我，就只能躲在阴暗的角落里，想要借刀杀人，传我和别的男人的绯闻，然后利用我粉丝对我的爱，想让我粉丝把我一刀捅死是吧。
真的很恐怖，连外卖都不敢点了，就怕有人蹲在我家门口，我一开门“你就是浅川玉乃是吧 就是你偷看男主播是吧”然后 碰！给我一刀噶了
关于我看这个主播，是从我小时开始就在看，之前的视频里也有说过，他真的是一个非常非常好，非常非常正能量的人，我从他身上学到了很多做人的道理。而且，他也有一个妹妹，然后我有一个哥哥。而且他和她妹妹的年龄差和我和我哥的年龄差差不多，他需要赚钱养妹妹，我需要赚钱养家，所以我感觉，他愿意搭理一个我这样的小粉丝，应该也有一些共鸣吧。
所以真的不要把所有人对主播的喜欢和支持都想得那么肮脏，不是所有人给主播送礼物都是想要追求主播想和主播结婚。但是那个开小号盒我的人，肯定是这样想的。他觉得我看男主播，就是喜欢他，对他有非分之想，就觉得我的粉丝很傻逼，想利用他们一刀捅死我。
以及我觉得，人肉这个事情，本来就是违法的，我们应该痛斥这个盒狗。我和我的粉丝都没有做错什么，做错的是这个盒狗。
然后我注销账号的原因，第一是因为我想让我的粉丝安心，我真的不想和这个主播结婚，他就是我哥哥、我偶像、我想成为的人的一个这样的存在，而且，人家那么优秀，也不会喜欢我。
第二，我认为过去的事情为何珍贵，珍贵的是你拥有的这一个独一无二的经历，它是刻在你的骨头里的是永远铭记于心的，是任何人都无法夺走的。而且，珍贵的不是“账号”而是“人”。我的偶像不会因为我换了一个账号就不认识我，回忆是相互的，他记得我的故事，记忆并不会因为账号的消失而消失。我喜欢的也只是他的灵魂，他积极向上的态度，和正能量的三观。
我们对于喜欢的人，给予支持、传达爱意，但是不能太过于极端，喜欢一个人，并不一定就要得到她。只需要看到她在你能看到的地方过得很好，有因为你的支持越来越好，就好了。偶像的存在，更多的是传达梦想，以及积极的共鸣，和粉丝共勉，共同进步，越过越好。
不要让爱，变成一种枷锁。
我永远也不会想要得到我的偶像，因为星星，只需要在我看得见的地方闪闪发光就好了。'''
    # ccid = 42177257
    # dmid = 30370332169732101
    # pprint(get_user_videos(3461565011462803)[0])
    # pprint(get_up_info(3461565011462803))
    # pprint(Crawl.get_space_info(5970160))
    # pprint(get_date_range('https://www.bilibili.com/video/BV1ms4y117ow/?vd_source=58a41ac877c965b4616d2d9f764c219d'))
    # pprint(Crawl.get_space_info(276134779))
    # print(auto_wrap(text))
    # Crawl.get_dm_likes(ccid, dmid)
