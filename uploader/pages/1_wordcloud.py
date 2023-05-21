import streamlit as st
from streamlit import session_state as sst

from lib.draw import show_user_cloud

if 'uid' not in sst:
    st.error('Please start from information page.')
    st.stop()

with st.sidebar:
    gen = st.button('Generate', on_click=show_user_cloud)
