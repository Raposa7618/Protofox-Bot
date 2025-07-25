from flask import Flask, render_template
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
def index():
    return "To vivo"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
