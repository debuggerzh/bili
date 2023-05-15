from copy import deepcopy
from datetime import datetime, timedelta
from pprint import pprint

import pandas as pd
import streamlit as st
from pymysql.connections import Connection
from sqlalchemy import Column, Integer, String, Text, Float, Result, func
from sqlalchemy import create_engine, BigInteger, SmallInteger, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from lib.crc32 import crack
from lib.util import Crawl, get_up_info

engine = create_engine('mysql+pymysql://root:123456@localhost/bili')
Session = sessionmaker(bind=engine)
Base = declarative_base()


class Series(Base):
    __tablename__ = 'series'

    mid = Column(Integer, primary_key=True)
    name = Column(String(255))


class User(Base):
    __tablename__ = 'user'

    uid = Column(BigInteger, primary_key=True)
    name = Column(String(255))
    sex = Column(SmallInteger())
    birthday = Column(String(5))
    face = Column(String(255))
    fans = Column(Integer)
    level = Column(SmallInteger())  # -1表示号寄了
    school = Column(String(255))
    sign = Column(String(255))
    v_num = Column(Integer)
    # todo 代表作存在冗余
    pic = Column(String(255))  # 代表作封面
    title = Column(String(255))
    desc = Column(Text)


class Video(Base):
    __tablename__ = 'video'

    cid = Column(Integer, primary_key=True)
    title = Column(String(255))
    bvid = Column(String(12))
    aid = Column(Integer)
    mid = Column(Integer, ForeignKey('series.mid'))
    tags = Column(String(255))
    pic = Column(String(255))

    view = Column(Integer)
    danmaku = Column(Integer)
    reply = Column(Integer)
    favorite = Column(Integer)
    coin = Column(Integer)
    share = Column(Integer)
    like = Column(Integer)
    desc = Column(Text)


class Danmaku(Base):
    __tablename__ = 'danmaku'

    dmid = Column(BigInteger, primary_key=True)
    time = Column(Float)
    text = Column(String(255))
    mode = Column(Integer)
    size = Column(Integer)
    color = Column(Integer)
    date = Column(Integer)
    cid = Column(Integer, ForeignKey('video.cid'))
    uid = Column(BigInteger, ForeignKey('user.uid'))


def query_danmaku_by_date(cid: int, fmt_date: str):
    # 转换为一天的时间戳范围
    if not has_danmaku(cid):
        init_danmaku(cid)
    fmt = '%Y-%m-%d'
    this_day = datetime.strptime(fmt_date, fmt)
    start = int(this_day.timestamp())
    one_day = timedelta(days=1)
    end = int((this_day+one_day).timestamp())
    session = Session()
    with session.begin():   # 左开右闭
        dmks = session.query(Danmaku.text).filter(Danmaku.cid == cid,
                                                  Danmaku.date >= start,
                                                  Danmaku.date < end).all()
    if dmks:
        return [x[0] for x in dmks]
    else:
        return []


def add_video(**kwargs):
    session = Session()
    with session.begin():
        session.add(Video(**kwargs))


def upd_video(cid: int, **kwargs):
    session = Session()
    with session.begin():
        video = session.query(Video).filter(Video.cid == cid).first()
        video.__dict__.update(kwargs)


def query_video(cid: int):
    session = Session()
    with session.begin():
        res: Result = session.query(Video).filter(Video.cid == cid)
        video = res.first()
        if not video:
            return
        else:
            new_video = deepcopy(vars(video))
            return new_video


@st.cache_data
def get_all_danmaku_text(cid: int):
    if not has_danmaku(cid):
        init_danmaku(cid)
    session = Session()
    with session.begin():
        dmks = session.query(Danmaku.text).filter(Danmaku.cid == cid).all()
    return [x[0] for x in dmks]


def has_danmaku(cid: int):
    session = Session()
    with session.begin():
        count = session.query(func.count('*')).filter(Danmaku.cid == cid).scalar()
    return True if count else False


def init_danmaku(cid: int):
    session = Session()
    with session.begin():
        soup = Crawl.get_danmakus_from_xml(cid, True)
        for danmaku in soup.find_all('d'):
            properties = danmaku['p'].split(',')
            dmid = properties[-2]  # 弹幕ID
            time = properties[0]
            text = danmaku.text
            mode = properties[1]  # 8代表高级弹幕
            size = properties[2]  # 25为默认值
            color = properties[3]  # 十进制
            date = properties[4]
            # uhash十六进制，这里B站做了调整，在最后增加了weight参数
            uhash = properties[-3]
            uid = crack(uhash)
            user_data = get_up_info(uid)
            add_user(uid, **user_data)
            session.add(Danmaku(dmid=dmid, time=time, text=text, mode=mode,
                                size=size, color=color, date=date,
                                cid=cid, uid=uid))
            print(uid, dmid)


def has_user(uid: int):
    session = Session()
    with session.begin():
        count = session.query(func.count('*')).filter(User.uid == uid).scalar()
    return True if count else False


def query_user(uid: int):
    session = Session()
    with session.begin():
        res: Result = session.query(User).filter(User.uid == uid)
        user = res.first()
        if not user:
            return
        else:
            new = deepcopy(vars(user))
            return new


def upd_user(uid: int, **kwargs):
    session = Session()
    with session.begin():
        user = session.query(User).filter(User.uid == uid).first()
        user.__dict__.update(kwargs)


def add_user(uid: int, **kwargs):
    if kwargs['sex'] == '女':
        kwargs['sex'] = 0
    elif kwargs['sex'] == '男':
        kwargs['sex'] = 1
    else:
        kwargs['sex'] = 2
    session = Session()
    with session.begin():
        if not has_user(uid):
            session.add(User(uid=uid, **kwargs))


class DBUtil:
    __instance = None
    conn: Connection = None

    # 惰性单例模式
    def __new__(cls, *args, **kwargs):
        if cls.__instance:  # 自动销毁前一个
            del cls.__instance
        cls.__instance = object.__new__(cls)
        return cls.__instance

    def __init__(self, **kwargs):
        # DBUtil.make_conn()
        self.title = kwargs['title']
        self.aid = kwargs['aid']
        self.bvid = kwargs['bvid']
        self.cid = kwargs['cid']
        self.tags = kwargs['tags']
        self.pic = kwargs['pic']
        self.desc = kwargs['desc']
        # 以下为统计数据
        self.view = kwargs['view']
        self.danmaku = kwargs['danmaku']
        self.reply = kwargs['reply']
        self.favorite = kwargs['favorite']
        self.coin = kwargs['coin']
        self.share = kwargs['share']
        self.like = kwargs['like']

        self.insert2video()

    @staticmethod
    def make_conn():
        # if not DBUtil.conn:
        import pymysql
        conn = pymysql.connect(
            user='root', password='123456', host='localhost', database='bili',
            charset='utf8mb4', cursorclass=pymysql.cursors.Cursor
        )
        return conn

    def create_table(self):
        conn = self.make_conn()
        with conn:
            with conn.cursor() as cursor:
                cursor.execute('SHOW TABLES')
                print(self.bvid)
                if self.bvid in [x[0] for x in cursor]:
                    return  # 表已存在

                sql = """CREATE TABLE {} (
                time FLOAT, 
                text VARCHAR(255) CHARACTER SET utf8, 
                mode INT, 
                size INT, 
                color INT, 
                date INT, 
                user VARCHAR(255), 
                dmid BIGINT)""".format(self.bvid)
                print(sql)
                print(cursor.execute(sql))
            conn.commit()

    def init_danmaku(self):
        conn = self.make_conn()
        with conn:
            with conn.cursor() as cursor:
                sql = '''INSERT INTO danmaku VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s
                )'''
                cid = self.cid
                soup = Crawl.get_danmakus_from_xml(cid, True)
                for danmaku in soup.find_all('d'):
                    properties = danmaku['p'].split(',')
                    dmid = properties[-2]  # 弹幕ID
                    time = properties[0]
                    text = danmaku.text
                    mode = properties[1]  # 8代表高级弹幕
                    size = properties[2]  # 25为默认值
                    color = properties[3]  # 十进制
                    date = properties[4]
                    # uhash十六进制，这里B站做了调整，在最后增加了weight参数
                    uhash = properties[-3]
                    uid = crack(uhash)
                    self.insert_user(uid)
                    cursor.execute(sql, (dmid, time, text, mode, size,
                                         color, date, cid, uid))
            conn.commit()

    def has_data(self):
        conn = self.make_conn()
        with conn:
            sql = 'SELECT COUNT(*) FROM `danmaku` WHERE cid={}'.format(self.cid)
            with conn.cursor() as cursor:
                cursor.execute(sql)
                res = cursor.fetchone()
                return True if res[0] else False

    @st.cache_data
    def get_all_text(_self):
        if not _self.has_data():
            _self.init_danmaku()

        conn = _self.make_conn()
        with conn:
            sql = 'SELECT `text` FROM danmaku WHERE cid={}'.format(_self.cid)
            with conn.cursor() as cursor:
                cursor.execute(sql)
                res = cursor.fetchall()
                return [x[0] for x in res]

    @staticmethod
    @st.cache_data
    def get_all2df(cid: int):
        if not has_danmaku(cid):
            init_danmaku(cid)

        conn = DBUtil.make_conn()
        with conn:
            sql = "SELECT * FROM danmaku WHERE cid={}".format(cid)
            # with DBUtil.conn.cursor() as c:
            #     c.execute(sql)
            #     res = c.fetchall()
            df = pd.read_sql(sql, conn)
            return df

    @staticmethod
    @st.cache_data
    def get_all2df_by_date(cid: int, fmt_date: str):
        if not has_danmaku(cid):
            init_danmaku(cid)
        fmt = '%Y-%m-%d'
        this_day = datetime.strptime(fmt_date, fmt)
        start = int(this_day.timestamp())
        one_day = timedelta(days=1)
        end = int((this_day + one_day).timestamp())
        conn = DBUtil.make_conn()
        with conn:
            sql = "SELECT * FROM danmaku WHERE cid=%s AND `date`>=%s AND `date`<%s"
            # with DBUtil.conn.cursor() as c:
            #     c.execute(sql)
            #     res = c.fetchall()
            params = (cid, start, end)
            df = pd.read_sql(sql, conn, params=params)
            return df

    def insert2video(self):
        conn = self.make_conn()
        with conn:
            sql = '''INSERT INTO `video` VALUES (
            %s, %s, %s, %s, null, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s
            )'''
            with conn.cursor() as cursor:
                from pymysql import IntegrityError
                try:
                    cursor.execute(sql,
                                   (self.title, self.cid, self.bvid,
                                    self.aid, self.tags, self.pic,
                                    self.view, self.danmaku, self.reply, self.favorite,
                                    self.coin, self.share, self.like, self.desc))
                except IntegrityError as e:
                    print(e)
            conn.commit()

    def query_video(self):
        pass

    def insert_user(self, uid):
        conn = self.make_conn()
        with conn:
            data = Crawl.get_space_info(uid)
            uname = data['name']
            gender = data['sex']
            if gender == '女':
                gender = 0
            elif gender == '男':
                gender = 1
            else:
                gender = 2
            sql = '''INSERT INTO `user` VALUES (
            %s, %s, %s
            )'''.format(gender)
            with conn.cursor() as cursor:
                from pymysql import IntegrityError
                try:
                    cursor.execute(sql, (uid, uname, gender,))
                except IntegrityError as e:
                    print(e)
            conn.commit()


if __name__ == '__main__':
    pprint(query_danmaku_by_date(319612214, '2021-04-04'))
