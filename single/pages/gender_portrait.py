from collections import Counter
import pandas as pd
import streamlit as st
import plotly.express as px

from lib.bert_classify import classify_test
from lib.crc32 import crack
from lib.db import DBUtil
from lib.util import Crawl

if 'meta' not in st.session_state:
    st.error('Please start from infomation page.')
    st.stop()

c = Counter(correct=3302, wrong=218, fail=80)
df = pd.DataFrame(list(c.items()), columns=['label', 'value'])
fig = px.pie(df, values='value', names='label',
             color_discrete_sequence=('green', 'yellow', 'red'))
st.plotly_chart(fig)
st.stop()

c = Counter(correct=0, wrong=0, fail=0)
dbutil: DBUtil = st.session_state.dbutil
df = dbutil.get_all2df()
df = classify_test(df)
for row in df.itertuples():
    uid = crack(row.user)
    gender = Crawl.get_gender(uid)
    if gender == -1:
        c['fail'] += 1
    else:
        if gender == row.p_gender:
            c['correct'] += 1
        else:
            c['wrong'] += 1

df = pd.DataFrame(list(c.items()), columns=['label', 'value'])
fig = px.pie(df, values='value', names='label',
             color_discrete_sequence=('green', 'yellow', 'red'))
st.plotly_chart(fig)
