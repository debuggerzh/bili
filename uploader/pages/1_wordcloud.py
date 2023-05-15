import streamlit as st
from streamlit import session_state as sst

from lib.draw import st_draw_user_wordcloud

if 'uid' not in sst:
    st.error('Please start from information page.')
    st.stop()


def show_cloud():
    uid = st.session_state.uid
    figure = st_draw_user_wordcloud(uid)
    st.pyplot(figure)


with st.sidebar:
    gen = st.button('Generate', on_click=show_cloud)
