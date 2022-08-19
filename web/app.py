from flask import Flask, render_template, request, abort
import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mh_bot_super_botHAHAHAHA&'

CLIENT_ID = 613645592241111040
CLIENT_SECRET = "wEg-nluGfzGeu3n7NvDXQPqTRMlk5kPE"
REDIRECT_URI = "http://127.0.0.1:5000"
API_ENDPOINT = "https://discord.com/api"

logged = [("ip_addr", "invite_code")]


class Writer:
    def __init__(self):
        self.text = []

    def write(self, line):
        self.text.append(str(line))

    def __str__(self):
        return "\n".join(self.text)


def exchange_code(code):

    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    r = requests.post('%s/oauth2/token' % API_ENDPOINT, data=data, headers=headers)
    return r.json()


def get_user(exchanged_code):
    headers = {
        'Authorization': f"{exchanged_code['token_type']} {exchanged_code['access_token']}"
    }
    return requests.get('https://discord.com/api/users/@me', headers=headers).json()


@app.route('/')
def index():
    body = Writer()
    code = request.args.get('code')

    if not code:
        abort(400)

    code = exchange_code(code)
    if 'error' in code:
        abort(400)

    print(get_user(code))

    # body.write(get_user())

    return render_template("index.html", body=str(body))


@app.route('/invite')
def invite(code: int = None):
    print(request.remote_addr)
    print(request.args.get('code'))
    return render_template("index.html", body=code)


app.run("0.0.0.0", port=5000)
