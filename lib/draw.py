import os
import random
from datetime import datetime
import jieba
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
from collections import Counter
from PIL import Image
from matplotlib import pyplot as plt, ticker as mticker
from matplotlib.figure import Figure
from pandas import DataFrame
from streamlit import session_state as sst
from streamlit_profiler import Profiler
from wordcloud import WordCloud

from lib.db import query_danmaku_by_date, get_all_danmaku_text, DBUtil, query_video, get_series_all_text
from lib.meta import get_cid
from lib.profile import profile
from lib.sentiment import sentiment_analyze, get_distribution
from lib.util import util, Contstant, Crawl, get_date_range, convert_df, get_user_videos, get_metadata

__all__ = ['st_draw_sentiment', 'draw_history_bars', 'draw_multi_history_bars',
           'draw_pie', 'draw_multi_radar_graph', 'draw_stacked_bars_graph',
           'draw_heat_curve', 'draw_multi_curve', 'draw_series_sentiment']


@st.cache_data
def draw_pie(dfm: DataFrame, **kwargs) -> Figure:
    """
    画全部弹幕的主客观饼图
    :return:
    """
    # dfm = Crawl.crawl_save(file, cid)
    with Profiler():
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


@profile
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
    with Profiler():
        # dfm = Crawl.crawl_save(file, cid)
        interval = (duration - 1) // intervals + 1
        result = get_distribution(dfm, duration, intervals, multi=True)
        fig, axs = plt.subplots(8, 1, sharex='all')
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
    # dmks = get_all_text(sst.meta['aid'])
    dmks = Crawl.crawl_save(file, cid)['text'].tolist()
    print(len(dmks), sum((len(x) for x in dmks)))
    return draw_wordcloud(dmks)


@st.cache_data
def draw_multi_history_bars(_vid: str, cid: int, samples: int):
    with Profiler():
        dt_range = get_date_range(_vid)
        # step = len(dt_range) // samples
        # if step:
        #     dt_range = dt_range[:step * samples:step]
        results = []
        selected_dt_range = []
        for dt in dt_range:
            # dmk_list = dm_history(cid, dt)
            dmk_list = query_danmaku_by_date(cid, dt)
            if len(dmk_list) == 0:
                continue
            counter, _ = sentiment_analyze(dmk_list, True)
            results.append(tuple(counter.values()))
            selected_dt_range.append(dt)
            if len(results) == samples:
                break
        fig, axs = plt.subplots(8, 1, sharex='all')
        labels = ('happy', 'like', 'anger', 'sad', 'surprise', 'disgust', 'fear', "multi")
        colors = ('cyan', 'yellow', 'red', 'blue', 'magenta', 'green', 'black', 'cyan')
        for i in range(8):
            line, = axs[i].plot(range(samples), [x[i] for x in results],
                                color=colors[i])
            line.set_label(labels[i])
        plt.xticks(range(samples), selected_dt_range, rotation=45)
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
    # todo 选取有效数据
    dt_range = get_date_range(_vid)
    # step = len(dt_range) // samples
    # if step:
    #     dt_range = dt_range[:step * samples:step]
    results = []
    selected_dt_range = []
    for dt in dt_range:
        # dmk_list = dm_history(cid, dt)
        dmk_list = query_danmaku_by_date(cid, dt)
        if len(dmk_list) == 0:
            continue
        counter, _ = sentiment_analyze(dmk_list)
        results.append(tuple(counter.values()))
        selected_dt_range.append(dt)
        if len(results) == samples:
            break
    st.write(results)

    posi = [x[0] for x in results]
    neu = [x[1] for x in results]
    nega = [x[-2] for x in results]
    obj = [x[-1] for x in results]

    width = .35
    fig: Figure = plt.figure()
    plt.subplot(2, 1, 1)
    plt.xticks([])
    index = np.arange(samples)
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
    plt.xticks(index, selected_dt_range, rotation=45)

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


def draw_series_multi(text: list[list[str]]) -> Figure:
    counters: list[Counter] = [sentiment_analyze(ep, multi=True)[0]
                               for ep in text]
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
    for tag, ax, color in zip(tags, axs, colors):
        line, = ax.plot(index, [x[tag] for x in counters], color=color)
        line.set_label(tag)
    plt.xlabel('Episodes')
    fig.legend()
    return fig


@st.cache_data
def draw_series_sentiment(mid: int,):
    text = get_series_all_text(mid)
    # dts: list[DataFrame] = []
    # episodes = _meta['episodes']
    # dmk_dir = os.path.join('series', str(mid))
    # if not os.path.exists(dmk_dir):
    #     os.mkdir(dmk_dir)
    # for ep in range(0, _meta['total']):
    #     csv_file = f'series\\{mid}\\{ep + 1}.csv'
    #     dts.append(Crawl.crawl_save(csv_file, episodes[ep]['cid']))
    return (draw_series_bars(text), draw_series_sentiment_curve(text),
            draw_series_multi(text))


def draw_series_bars(text: list[list[str]]):
    counters: list[Counter] = [sentiment_analyze(ep)[0] for ep in text]
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
    # plt.savefig(r'series\three\主客观分布.jpg')
    return fig


def draw_series_sentiment_curve(text: list[list[str]]):
    tots = [cal_sentiment_value(ep) for ep in text]
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


def cal_sentiment_value(text: list[str]):
    _, tot = sentiment_analyze(text)
    return tot  # 返回平均情感得分，已经计算过平均值


@st.cache_data
def st_draw_user_wordcloud(uid: int, v_num: int):
    # directory = os.path.join('resources', 'danmakus', uid)
    # if not os.path.exists(directory):
    #     os.mkdir(directory)
    # todo 加入下载功能
    videos = get_user_videos(uid)
    danmaku_list = []
    for idx in range(v_num):
        bvid = videos[idx]['bvid']
        cid = get_cid(bvid)
        dmks = get_all_danmaku_text(cid, bvid)
        danmaku_list.extend(dmks)
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


def show_cloud():
    with Profiler():
        metadata = sst.meta
        cid = metadata['cid']
        with st.spinner('正在生成弹幕词云...'):
            if sst.disable_history:  # 全弹幕
                df = DBUtil.get_all_danmaku2df(cid)
                # dmks = get_all_danmaku_text(cid)
                dmks = df['text'].tolist()
                fig = draw_wordcloud(dmks)
                # fig = st_draw_wordcloud(sst.csv, metadata['cid'])
                st.pyplot(fig)
                with st.spinner('正在准备下载...'):
                    st.info('请使用UTF-8编码打开')
                    # df: DataFrame = Crawl.crawl_save(sst.csv, metadata['cid'])
                    st.download_button('Download danmaku file',
                                       convert_df(df),
                                       os.path.basename(sst.csv),
                                       on_click=lambda: st.info('请使用UTF-8编码打开'),
                                       mime='text/csv')
            else:
                strftime = sst.date.strftime('%Y-%m-%d')
                df: DataFrame = DBUtil.get_all2df_by_date(cid, sst.date)
                if len(df) == 0:
                    st.error('这一天没有任何弹幕记录。')
                    st.stop()
                dmks = df['text'].tolist()
                # dmks = dm_history(cid, date)
                fig = draw_wordcloud(dmks)
                st.pyplot(fig)
                hist_file_path = os.path.join(os.path.dirname(sst.csv),
                                              f'{cid}_{strftime}.csv')
                st.download_button('Download danmaku file',
                                   convert_df(df),
                                   os.path.basename(hist_file_path),
                                   mime='text/csv')


def show_user_cloud():
    uid = sst.uid
    figure = st_draw_user_wordcloud(uid, 1)
    st.pyplot(figure)


def show_series_cloud():
    with st.spinner('正在生成弹幕词云...'):
        if sst.all:  # 全剧集词云
            if sst.disable_history:  # 禁历史
                text = get_series_all_text(sst.mid)
            else:
                text = get_series_all_text(sst.mid, sst.date)
            text = [word for ep in text for word in ep]
            figure = draw_wordcloud(text)
        else:  # 单集词云
            cid = sst.cid
            bvid = sst.bvid
            if sst.disable_history:
                text = get_all_danmaku_text(cid, bvid, sst.mid)
                figure = draw_wordcloud(text)
            else:
                text = get_all_danmaku_text(cid, bvid, sst.mid, sst.date)
                figure = draw_wordcloud(text)
        st.pyplot(figure)
