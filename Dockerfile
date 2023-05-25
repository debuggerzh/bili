# app/Dockerfile

FROM python:3.10-slim
# 直接clone到该目录下
WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# 将仓库clone至/app下
# RUN git clone https://github.com/debuggerzh/bili.git /app/bilipy
COPY . .
RUN pip3 install -r requirements.txt

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "info.py", "--server.port=8501", "--server.address=0.0.0.0"]
