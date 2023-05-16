import json
import os
import random
import jieba
import numpy as np
import pandas as pd
import requests
import streamlit as st
import plotly.express as px
from collections import Counter
from PIL import Image
from matplotlib import pyplot as plt, ticker as mticker
from matplotlib.figure import Figure
from pandas import DataFrame
from requests import RequestException
from wordcloud import WordCloud

from lib.db import query_danmaku_by_date
from lib.info import user_headers
from lib.meta import get_cid
from lib.sentiment import sentiment_analyze, get_distribution
from lib.util import util, Contstant, Crawl, get_date_range, dm_history

__all__ = ['st_draw_sentiment', 'draw_history_bars', 'draw_multi_history_bars',
           'draw_pie', 'draw_multi_radar_graph', 'draw_stacked_bars_graph',
           'draw_heat_curve', 'draw_multi_curve']


@st.cache_data
def draw_pie(dfm: DataFrame, **kwargs) -> Figure:
    """
    画全部弹幕的主客观饼图
    :return:
    """
    # dfm = Crawl.crawl_save(file, cid)
    counter, _ = sentiment_analyze(dfm['text'].tolist())
    df = pd.DataFrame(list(counter.items()), columns=['label', 'ratio'])
    figure = px.pie(df, values='ratio', names='label',
                    color_discrete_sequence=('blue', 'yellow', 'green', 'red'))
    return figure

    labels = list(counter)
    ratios = list(counter.values())
    fig, ax = plt.subplots()
    ax.pie(ratios, labels=labels)
    # plt.show()
    return fig


@st.cache_data
def draw_multi_radar_graph(dfm: DataFrame, **kwargs):
    # dfm = Crawl.crawl_save(file, cid)
    counter, _ = sentiment_analyze(dfm['text'].tolist(), multi=True)
    print(counter.items())
    df = pd.DataFrame(list(counter.items()), columns=['label', 'R'])
    figure = px.line_polar(df, r='R', theta='label', line_close=True,
                           color_discrete_sequence=['blue'], )
    figure.update_layout(polar=dict(bgcolor='lightgreen'))
    return figure

    arr = list(counter.values())
    N = 8
    labels = np.array(util.emotion_types + ['multi'])
    data = np.array(arr)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False)  # 左闭右开
    data = np.append(data, data[0])
    angles = np.append(angles, angles[0])
    labels = np.append(labels, labels[0])

    fig: Figure = plt.figure(facecolor="white")
    plt.subplot(111, polar=True)
    # 'bo-' means blue dot solid line
    plt.plot(angles, data, 'bo-', linewidth=2)
    plt.fill(angles, data, facecolor='g', alpha=0.25)
    plt.thetagrids(angles * 180 / np.pi, labels)
    plt.figtext(0.52, 0.95, 'Multi-sentiment Radar Graph', ha='center')
    plt.grid(True)
    return fig


@st.cache_data
def draw_stacked_bars_graph(dfm: DataFrame, duration: int, intervals: int):
    # df = Crawl.crawl_save(file, cid)
    interval = (duration - 1) // intervals + 1
    results = get_distribution(dfm, duration, intervals)
    N = len(results)
    width = .35
    index = np.arange(N)
    posi = [x[0] for x in results]
    neu = [x[1] for x in results]
    nega = [x[-2] for x in results]
    obj = [x[-1] for x in results]
    # 以下绘制绝对分布
    fig: Figure = plt.figure()
    plt.subplot(2, 1, 1)
    p1 = plt.bar(index, obj, width)
    p2 = plt.bar(index, nega, width, bottom=obj)
    p3 = plt.bar(index, neu, width, bottom=np.add(obj, nega))
    p4 = plt.bar(index, posi, width, bottom=np.add(np.add(obj, nega), neu))
    plt.xticks([])  # 清除轴标签
    plt.legend((p1, p2, p3, p4), ('Objective', 'Negative', 'Neutral', 'Positive'))
    plt.title('Absolute Distribution')
    # 以下绘制相对分布
    plt.subplot(2, 1, 2)
    # 若该时间段内无弹幕，直接记为0，规避除零错误
    posi = [x[0] / sum(x) * 100 if sum(x) else 0 for x in results]
    neu = [x[1] / sum(x) * 100 if sum(x) else 0 for x in results]
    nega = [x[-2] / sum(x) * 100 if sum(x) else 0 for x in results]
    obj = [x[-1] / sum(x) * 100 if sum(x) else 0 for x in results]
    plt.gca().yaxis.set_major_formatter(mticker.FormatStrFormatter('%d%%'))
    plt.bar(index, obj, width)
    plt.bar(index, nega, width, bottom=obj)
    plt.bar(index, neu, width, bottom=np.add(obj, nega))
    plt.bar(index, posi, width, bottom=np.add(np.add(obj, nega), neu))
    plt.xlabel(f'Time/{interval}s')
    plt.xticks(range(0, len(results), 2), range(0, len(results), 2))
    plt.title('Relative Distribution')
    plt.tight_layout()  # 自动校正，避免文字重叠
    return fig


@st.cache_data
def draw_heat_curve(dfm: DataFrame, duration: int, intervals: int):
    """
    绘制一个表示热度曲线的折线图，以直代曲
    :param dfm:
    :param intervals:
    :param duration:
    :return:
    """
    # dfm = Crawl.crawl_save(file, cid)
    interval = (duration - 1) // intervals + 1
    result = get_distribution(dfm, duration, intervals, True)
    x = range(intervals)
    df = DataFrame(list(zip(x, result)), columns=['nth', 'value'])
    figure = px.line(df, x='nth', y='value', color_discrete_sequence=['green'],
                     labels={'nth': '经过时间间隔数', 'value': '综合热度值'})
    figure.update_layout(xaxis_title=f'Time/{interval}s')
    return figure

    fig: Figure = plt.figure()
    plt.plot(x, result, "g", marker='D', markersize=5, label="Heat Value")
    plt.xlabel(f'Time/{interval}s')
    plt.xticks(range(0, len(result), 2), range(0, len(result), 2))
    # plt.ylabel("")
    plt.title("Heat value simulation")
    plt.legend(loc="lower right")
    for x1, y1 in zip(x, result):
        plt.text(x1, y1, str(y1), ha='center', va='bottom', fontsize=10)
    return fig


@st.cache_data
def draw_multi_curve(dfm: DataFrame, duration: int, intervals: int):
    # dfm = Crawl.crawl_save(file, cid)
    interval = (duration - 1) // intervals + 1
    result = get_distribution(dfm, duration, intervals, multi=True)
    fig, axs = plt.subplots(8, 1, sharex=True)
    labels = ('happy', 'like', 'anger', 'sad', 'surprise', 'disgust', 'fear', "multi")
    colors = ('cyan', 'yellow', 'red', 'blue', 'magenta', 'green', 'black', 'cyan')
    for i in range(8):
        line, = axs[i].plot(range(intervals), [x[i] for x in result], color=colors[i])
        line.set_label(labels[i])
    plt.xlabel(f'Time/{interval}s')
    fig.legend()
    return fig


@st.cache_data
# todo 仅认为filename不变时，画出的图也不变，故可考虑增加索引以提高准确性
def st_draw_wordcloud(file, cid):
    """

    :return : 返回弹幕词云figure
    """
    # from lib.db import get_all_text
    # dmks = get_all_text(st.session_state.meta['aid'])
    dmks = Crawl.crawl_save(file, cid)['text'].tolist()
    print(len(dmks), sum((len(x) for x in dmks)))
    return draw_wordcloud(dmks)


@st.cache_data
def draw_multi_history_bars(_vid: str, cid: int, samples: int):
    dt_range = get_date_range(_vid)
    step = len(dt_range) // samples
    if step:
        dt_range = dt_range[:step * samples:step]
    results = []
    for dt in dt_range:
        # dmk_list = dm_history(cid, dt)
        dmk_list = query_danmaku_by_date(cid, dt)
        counter, _ = sentiment_analyze(dmk_list, True)
        results.append(tuple(counter.values()))
    fig, axs = plt.subplots(8, 1, sharex='all')
    labels = ('happy', 'like', 'anger', 'sad', 'surprise', 'disgust', 'fear', "multi")
    colors = ('cyan', 'yellow', 'red', 'blue', 'magenta', 'green', 'black', 'cyan')
    for i in range(8):
        line, = axs[i].plot(range(len(dt_range)), [x[i] for x in results], color=colors[i])
        line.set_label(labels[i])
    plt.xticks(range(len(dt_range)), dt_range, rotation=45)
    fig.legend()
    return fig


@st.cache_data
def draw_history_bars(_vid: str, cid: int, samples: int):
    """

    :param _vid:
    :param cid:
    :param samples: 日期取样量
    :return:
    """
    # todo 目前的历史弹幕是堆积数据，可以去重处理
    dt_range = get_date_range(_vid)
    step = len(dt_range) // samples
    if step:
        dt_range = dt_range[:step * samples:step]
    # avbvid = avbvid_pattern.search(vid).group(0)
    # cur_directory = os.path.join('resources', 'danmakus', avbvid)
    # if not os.path.exists(cur_directory):
    #     os.mkdir(cur_directory)
    results = []
    for dt in dt_range:
        # dmk_list = dm_history(cid, dt)
        dmk_list = query_danmaku_by_date(cid, dt)
        counter, _ = sentiment_analyze(dmk_list)
        results.append(tuple(counter.values()))
    posi = [x[0] for x in results]
    neu = [x[1] for x in results]
    nega = [x[-2] for x in results]
    obj = [x[-1] for x in results]

    width = .35
    fig: Figure = plt.figure()
    plt.subplot(2, 1, 1)
    plt.xticks([])
    index = np.arange(len(dt_range))
    p1 = plt.bar(index, obj, width)
    p2 = plt.bar(index, nega, width, bottom=obj)
    p3 = plt.bar(index, neu, width, bottom=np.add(obj, nega))
    p4 = plt.bar(index, posi, width, bottom=np.add(np.add(obj, nega), neu))
    plt.legend((p1, p2, p3, p4), ('Objective', 'Negative', 'Neutral', 'Positive'))

    plt.subplot(2, 1, 2)
    posi = [x[0] / sum(x) * 100 if sum(x) else 0 for x in results]
    neu = [x[1] / sum(x) * 100 if sum(x) else 0 for x in results]
    nega = [x[-2] / sum(x) * 100 if sum(x) else 0 for x in results]
    obj = [x[-1] / sum(x) * 100 if sum(x) else 0 for x in results]
    plt.gca().yaxis.set_major_formatter(mticker.FormatStrFormatter('%d%%'))
    plt.bar(index, obj, width)
    plt.bar(index, nega, width, bottom=obj)
    plt.bar(index, neu, width, bottom=np.add(obj, nega))
    plt.bar(index, posi, width, bottom=np.add(np.add(obj, nega), neu))
    plt.xticks(range(0, len(dt_range)), dt_range, rotation=45)
    plt.tight_layout()
    return fig


@st.cache_data
# 变量前的下划线表示不被索引
def st_draw_sentiment(csv_file: str, cid: int, intervals: int, _url: str,
                      _duration: int = 0):
    _dtfm = Crawl.crawl_save(csv_file, cid)
    # B站脑瘫，同样的字段番剧视频用毫秒单位，其他投稿用秒
    # 这种处理会错判duration正好为整千秒的视频，whatever
    if _duration % 1000 == 0:
        _duration //= 1000
    return (draw_pie(_dtfm), draw_multi_radar_graph(_dtfm),
            draw_stacked_bars_graph(_dtfm, intervals),
            draw_heat_curve(_dtfm, intervals),
            draw_multi_curve(_dtfm, intervals)
            )


def draw_series_multi(dts: list[DataFrame]) -> Figure:
    counters: list[Counter] = [sentiment_analyze(dt['text'].tolist(), multi=True)[0]
                               for dt in dts]
    N = len(counters)
    width = .35
    index = np.arange(N)
    tags = ('happy', 'like', 'anger', 'sad', 'surprise', 'disgust', 'fear', 'multi')
    hap = [x['happy'] for x in counters]
    lik = [x['like'] for x in counters]
    ang = [x['anger'] for x in counters]
    sad = [x['sad'] for x in counters]
    surp = [x['surprise'] for x in counters]
    dis = [x['disgust'] for x in counters]
    fear = [x['fear'] for x in counters]
    mul = [x['multi'] for x in counters]

    fig, axs = plt.subplots(8, 1, sharex='all')
    colors = ('cyan', 'yellow', 'red', 'blue', 'magenta', 'green', 'black', 'cyan')
    for tag, ax in zip(tags, axs):
        line, = ax.plot(index, [x[tag] for x in counters], color=random.choice(colors))
        line.set_label(tag)
    plt.xlabel('Episodes')
    fig.legend()
    return fig


@st.cache_data
def draw_series_sentiment(mid: int, _meta: dict):
    dts: list[DataFrame] = []
    episodes = _meta['episodes']
    dmk_dir = os.path.join('series', str(mid))
    if not os.path.exists(dmk_dir):
        os.mkdir(dmk_dir)
    for ep in range(0, _meta['total']):
        csv_file = f'series\\{mid}\\{ep + 1}.csv'
        dts.append(Crawl.crawl_save(csv_file, episodes[ep]['cid']))
    return (draw_series_bars(dts), draw_series_sentiment_curve(dts),
            draw_series_multi(dts))


def draw_series_bars(dts: list[DataFrame]):
    counters: list[Counter] = [sentiment_analyze(dt['text'].tolist())[0] for dt in dts]
    N = len(counters)
    width = .35
    index = np.arange(N)
    posi = [x['positive'] for x in counters]
    neu = [x['neutral'] for x in counters]
    nega = [x['negative'] for x in counters]
    obj = [x['objective'] for x in counters]

    fig: Figure = plt.figure()
    plt.subplot(2, 1, 1)  # 2rows,1column, 1st
    p1 = plt.bar(index, obj, width)
    p2 = plt.bar(index, nega, width, bottom=obj)
    p3 = plt.bar(index, neu, width, bottom=np.add(obj, nega))
    p4 = plt.bar(index, posi, width, bottom=np.add(np.add(obj, nega), neu))
    plt.xticks(range(0, len(counters), 4), range(0, len(counters), 4))
    # plt.yticks()
    plt.legend((p1, p2, p3, p4), ('Objective', 'Negative', 'Neutral', 'Positive'))
    # plt.title = 'Lex'
    plt.title('Absolute Distribution')

    plt.subplot(2, 1, 2)
    posi = [x['positive'] / x.total() * 100 for x in counters]
    neu = [x['neutral'] / x.total() * 100 for x in counters]
    nega = [x['negative'] / x.total() * 100 for x in counters]
    obj = [x['objective'] / x.total() * 100 for x in counters]

    p1 = plt.bar(index, obj, width)
    p2 = plt.bar(index, nega, width, bottom=obj)
    p3 = plt.bar(index, neu, width, bottom=np.add(obj, nega))
    p4 = plt.bar(index, posi, width, bottom=np.add(np.add(obj, nega), neu))
    plt.xlabel('Episodes')
    plt.xticks(range(0, len(counters), 4), range(0, len(counters), 4))
    # plt.yticks()
    plt.legend((p1, p2, p3, p4), ('Objective', 'Negative', 'Neutral', 'Positive'))
    # plt.title = 'Lex'
    plt.title('Relative Distribution')
    plt.savefig(r'series\three\主客观分布.jpg')
    return fig


def draw_series_sentiment_curve(dts: list[DataFrame]):
    tots = [cal_sentiment_value(dt) for dt in dts]
    N = len(tots)
    x = range(1, N + 1)
    fig: Figure = plt.figure()
    plt.plot(x, tots, "g", marker='D', markersize=5, label="Heat Value")
    plt.xlabel("Episodes")
    plt.xticks(range(0, N, 2), range(0, N, 2))
    # plt.ylabel("")
    plt.title("Sentiment value simulation")
    plt.legend(loc="lower right")
    for x1, y1 in zip(x, tots):
        plt.text(x1, y1, str(y1), ha='center', va='bottom', fontsize=10)
    return fig


def cal_sentiment_value(dt: DataFrame):
    _, tot = sentiment_analyze(dt['text'].tolist())
    return tot  # 返回平均情感得分，已经计算过平均值


@st.cache_data
def st_draw_user_wordcloud(uid):
    directory = os.path.join('resources', 'danmakus', uid)
    if not os.path.exists(directory):
        os.mkdir(directory)
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
    danmaku_list = []
    for v in videos:
        bvid = v['bvid']
        cid = get_cid(bvid)
        df = Crawl.crawl_save(os.path.join(directory, f'{bvid}.csv'), cid)
        danmaku_list.extend(df['text'])
    figure = draw_wordcloud(danmaku_list)
    return figure


def draw_wordcloud(dmks: list[str]):
    """

    :param dmks:
    :return: matplotlib.pyplot figure.
    """
    processed_words = []
    my_wordlist = []
    for danmaku in dmks:
        processed_words.extend(jieba.cut(danmaku))
    with open(util.stop_words_path, encoding='utf-8') as f_stop:
        f_stop_text = f_stop.read()
        f_stop_seg_list = f_stop_text.splitlines()
    for word in processed_words:
        if word not in f_stop_seg_list and len(word) > 0:
            my_wordlist.append(word)
    back_coloring = np.array(Image.open(Contstant.back_path))
    wc = WordCloud(font_path=Contstant.font_path, background_color="white", max_words=2000, mask=back_coloring,
                   max_font_size=100, random_state=42, width=1000, height=860, margin=2,
                   scale=32)
    wc.generate(' '.join(my_wordlist))
    fig: Figure = plt.figure()
    plt.imshow(wc, interpolation="bilinear")
    plt.axis("off")
    return fig
