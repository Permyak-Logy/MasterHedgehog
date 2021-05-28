from flask import Flask
from cogs.private_channels import PrivateChannelsBP

app = Flask(__name__)
app.register_blueprint(PrivateChannelsBP.blueprint, url_prefix='/private_channels')

app.run('127.0.0.1', port=5000)
