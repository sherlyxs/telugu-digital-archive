FROM python:3.9

WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt

EXPOSE 7860

CMD ["streamlit", "run", "app.py", "--server.port=7860", "--server.enableCORS=false"]
