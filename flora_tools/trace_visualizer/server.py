import os

from flask import Flask
from flask import render_template


class VisualizationServer:
    def __init__(self):
        abspath = os.path.abspath(__file__)
        dname = os.path.dirname(abspath)
        os.chdir(dname)

        self.app = Flask(__name__)

        @self.app.route('/')
        def index():
            return render_template('index.html')

        self.app.run(debug=True)
