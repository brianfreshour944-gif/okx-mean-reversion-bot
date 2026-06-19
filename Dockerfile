FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
# If you rename bot.py to main.py, change this line:
CMD ["python", "-u", "main.py"]
