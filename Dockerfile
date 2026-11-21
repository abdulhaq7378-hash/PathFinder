FROM python:3.11-slim
WORKDIR /app
COPY src/main.py /app/main.py
# main.py needs only the Python standard library
ENTRYPOINT ["python", "/app/main.py"]
CMD ["--help"]
