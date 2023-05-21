import streamlit as st

from lib.meta import show_user_info

with st.sidebar:
    st.text_input('Please input space url of the uploader:',
                  key='space_url',
                  help='Example: https://space.bilibili.com/108618052')
    flush = st.checkbox('Force flush database', key='flush')
    st.button('Generate', on_click=show_user_info, args=(st.session_state.flush,))
