from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive"

# In keep_alive.py, change the port to 10000
def run():
    app.run(host='0.0.0.0', port=10000)  # Avoid Render's default port 8080

def keep_alive():
    Thread(target=run).start()