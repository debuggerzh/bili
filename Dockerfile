# app/Dockerfile

FROM python:3.10-slim
# 直接clone到该目录下
WORKDIR /app/bili


# 将仓库clone至/app下
COPY requirements.txt .
# RUN git clone https://github.com/debuggerzh/bili.git /app/bilipy

ADD sources.list /etc/apt/ 
RUN apt-get update && apt-get install -y libmariadb-dev gcc

RUN pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple/ -U pip 
RUN pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple/
RUN pip3 install -r requirements.txt

COPY . .
EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "info.py", "--server.port=8501", "--server.address=0.0.0.0"]
