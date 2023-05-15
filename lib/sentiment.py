import jieba
import pandas as pd
from pandas import DataFrame
from collections import Counter

from lib.util import util, Contstant


def sentiment_analyze(danmaku_list: list[str], multi=False, debug=None):
    """
    主客观情感分析

    :param debug: 0-打印客观弹幕；1-打印like维弹幕
    :param multi: True则返回多维度分析结果
    :param danmaku_list: 要进行主客观情感分析的弹幕列表，一行一条
    :return : Counter(positive, neutral, negative, objective), 总情感得分
    or Counter(happy, like, anger, sad, surprise, disgust, fear, multi)
    """
    subjective = objective = 0
    positive = negative = neutral = 0
    tot_sentiment_value = 0
    multi_counter = Counter(happy=0, like=0, anger=0, sad=0, surprise=0, disgust=0, fear=0,
                            multi=0)

    for line in danmaku_list:
        # 为了能好好说话
        line = util.expand(line)
        sentiment = {}  # 代表每条弹幕中每个有效词的情感值
        words_of_sentence = [x for x in jieba.lcut(util.expand(line))
                             if x not in util.stop_words]
        # words_of_sentence = jieba.lcut(line)
        # 接下来查找情感词
        for i in range(len(words_of_sentence)):
            if words_of_sentence[i] in util.positive_words:
                point = Contstant.POSITIVE
            elif words_of_sentence[i] in util.negative_words:
                point = Contstant.NEGATIVE
            else:
                point = 0
            # 扫描情感词前的程度词以及否定词
            if i:   # 修复了重复计算的问题
                point *= util.match_adverb(words_of_sentence[i - 1])
                if words_of_sentence[i - 1] in util.inverse_words:
                    if words_of_sentence[i] in util.negative_words:
                        point = 0  # 负向被否定，趋向无情感
            # 处理感情标点
            if words_of_sentence[i] in ('!', '！'):
                if i and i - 1 in sentiment:
                    sentiment[i - 1] *= 2
            if words_of_sentence[i] in ('?', '？'):
                point = Contstant.NEGATIVE * -2

            sentiment[i] = point
        # all函数的妙用
        if all(v == 0 for v in sentiment.values()):
            objective += 1
            if debug == 0:
                print(line)
        else:  # 主观弹幕
            subjective += 1
            emotions = Counter(util.emotion_types)
            for index, value in sentiment.items():
                if value:
                    emotion = util.match_multi(words_of_sentence[index])
                    if emotion is None:  # 这意味多维情感词典未收录
                        continue
                    emotions[emotion] += 1
            final_emotions = [k for k, v in emotions.items() if v == max(emotions.values())]
            if len(final_emotions) == 1:
                pop = final_emotions.pop()
                if pop == 'like' and debug == 1:
                    print(line, [words_of_sentence[i]
                                 for i in range(len(sentiment)) if sentiment[i] > 0])
                multi_counter[pop] += 1
            elif len(final_emotions) == len(emotions):
                # 该句所有情感词均未被多维词典收录，重点排查
                # print(line, [words_of_sentence[x] for x in sentiment if sentiment[x]])
                pass
            else:
                multi_counter['multi'] += 1  # 两个维度情感值相同且最大

            tot_danmaku_value = sum(sentiment.values()) / len(sentiment)
            tot_sentiment_value += tot_danmaku_value
            if tot_danmaku_value > 0:
                positive += 1
            elif tot_danmaku_value == 0:
                neutral += 1
                # print(line)
            else:
                negative += 1
    if multi:
        return multi_counter, -1    # 配齐返回值，-1本身无意义
    avg = tot_sentiment_value / len(danmaku_list) if danmaku_list else 0
    return Counter(positive=positive, neutral=neutral, negative=negative,
                   objective=objective), round(avg, 2)


if __name__ == '__main__':
    pass
    # df = pd.read_csv(r'../resources/danmakus/975153366.csv')
    # print(sentiment_analyze(df['text'].tolist()))
    # with open(r'test.txt', encoding='utf-8') as f:
    #     print(sentiment_analyze(f.read().split('\n')))


def get_distribution(dfm: DataFrame, duration: int, intervals: int, heat=False,
                     debug=False, multi=False):
    """

    :param multi:
    :param dfm:
    :param duration:
    :param intervals: 片段数
    :param heat:
    :param debug:
    :return: 每个时间段的弹幕主客观情感或多维情感分布情况，或每个时间段的热度值
    """
    interval = (duration - 1) // intervals + 1
    result = []
    all_danmaku = len(dfm)  # 弹幕总条数
    tolist = dfm['text'].tolist()
    tot_len = len(''.join(tolist))  # 弹幕文本总长度
    tot_user = len(dfm.drop_duplicates(subset=['uid']))
    avg_value = sentiment_analyze(tolist)[1]

    for ith_min in range(intervals):
        ith_dfm = dfm[(dfm['time'] >= interval * ith_min) &
                      (dfm['time'] < interval * ith_min + interval)]
        ith_len = len(ith_dfm)
        part = ith_dfm['text'].to_list()
        counter, value = sentiment_analyze(part, multi)
        if debug:
            print(ith_min, counter)
        if heat:
            ith_user_distinct_dfm = ith_dfm.drop_duplicates(subset=['uid'])
            # 以下得到的均是100为满分的各子项
            if ith_len:
                tot_heat_point = int(100 - counter['objective'] / counter.total() * 100)
                tot_heat_point += int(len(ith_dfm) / all_danmaku * 100)
                tot_heat_point += int(len(''.join(ith_dfm['text'].tolist())) / tot_len * 100)
                tot_heat_point += int(len(ith_user_distinct_dfm) / tot_user * 100)
                tot_heat_point += int(len(ith_dfm[ith_dfm['color'] != 16777215])
                                      / ith_len * 100)
                tot_heat_point += int(len(ith_dfm[ith_dfm['size'] != 25]) / ith_len * 100)
                tot_heat_point += len(dfm[dfm['mode'] == 8]) * 10
                variance = (value - avg_value) ** 2 * 100
                tot_heat_point += variance
            else:
                tot_heat_point = 0
            result.append(tot_heat_point)
        else:
            result.append(list(counter.values()))
    return result
