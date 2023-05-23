from streamlit_profiler import Profiler


def profile(func):
    def wrapper(*args, **kwargs):
        p = Profiler()
        p.start()
        result = func(*args, **kwargs)
        p.stop()
        return result

    return wrapper
