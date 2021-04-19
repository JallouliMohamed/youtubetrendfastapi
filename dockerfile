FROM python:3.7

RUN pip freeze > requirements.txt

RUN pip install pandas fastapi uvicorn pymongo browser-cookie3 requests pydantic

EXPOSE 80

COPY ./app /app

CMD ["python","app/server.py"]
