import os
import json
import uuid
import traceback
from datetime import datetime
from redis import Redis
from rq import Queue, Retry
import requests
from flask import Flask, jsonify, request
from faqbot import FAQBot
import settings

app = Flask(__name__)
app.debug = True

def enqueue_question(func, api_id, question, response_url):
    q = Queue(connection=Redis())
    return q.enqueue(func, api_id, question, response_url, 
                     retry=Retry(max=3), 
                     job_timeout=settings.OPENAI_REQUEST_TIMEOUT*2)


class Logger(object):
    def __init__(self, api_id=None):
        self.base_log = {}
        self.api_id = api_id

    def log(self, level, msg, **data):
        _log = {'api_id': self.api_id, 
               'level': level,
               'timestamp': str(datetime.utcnow()),
               'msg': msg}
        _log.update(data)
        print(_log)

    def info(self, msg, **data):
        self.log('info', msg, **data)

    def error(self, msg, **data):
        self.log('error', msg, **data)

    def debug(self, msg, **data):
        self.log('debug', msg, **data)

    def warning(self, msg, **data):
        self.log('warning', msg, **data)

class APIResponse(object):
    def __init__(self, api_id=None):
        if not api_id:
            self.api_id = str(uuid.uuid4())
        else:
            self.api_id = api_id
        self.log = Logger(self.api_id)

    def error(self, msg, **data):
        data['status'] = 'error'
        data['error'] = msg
        self.log.error(msg, **data)
        return jsonify(data), 500

    def denied(self, **data):
        data['status'] = 'denied'
        data['error']: 'Access denied'
        self.log.error('Access denied', **data)
        return jsonify(data), 403

    def success(self, msg, **data):
        data['status'] = 'success'
        self.log.info(msg, **data)
        return jsonify(data), 200

    def get_api_id(self):
        return self.api_id

    def get_log(self):
        return self.log


@app.route('/', methods=['GET'])
def index():
    return APIResponse().success("Welcome to Plivo FAQBot API")

@app.route('/status', methods=['GET'])
def status():
    return APIResponse().success("OK")

@app.route('/dump', methods=['POST'])
def dump():
    api = APIResponse()
    api.get_log().info('############ Dumping request ############')
    api.get_log().info('Request headers', data=str(request.headers))
    api.get_log().info('Request values', data=str(request.values))
    api.get_log().info('Request data', data=str(request.data))
    api.get_log().info('############ End of dump ############')
    return api.success('OK')


@app.route('/ask', methods=['POST'])
def ask_bot():
    api = APIResponse()
    question = ''

    # paramaters sent by slack: 
    # ImmutableMultiDict([('token', 'xxxx'), ('team_id', 'xxxx'), ('team_domain', 'xxxx'), ('channel_id', 'xxxx'), ('channel_name', 'directmessage'), ('user_id', 'xxxx'), ('user_name', 'xxxx'), ('command', '/askplivo'), ('text', 'How can I send an MMS?'), ('api_app_id', 'xxxx'), ('is_enterprise_install', 'false'), ('enterprise_id', 'xxxxx'), ('enterprise_name', 'xxxxx'), ('response_url', 'https://hooks.slack.com/commands/xxxxx/yyyyy'), ('trigger_id', '12345650.2185784041.89264838048e2b69570fb84f2187a4ea')]

    if request.method != 'POST':
        return api.error('Invalid request method')

    try:
        try:
            token_id = request.form['token']
            user_name = request.form.get('user_name', None)
            team_domain = request.form.get('team_domain', None)
        except KeyError:
            return api.denied()

        if token_id != settings.SLACK_TOKEN_ID:
            return api.denied()

        cmd = request.form['command']
        if cmd != '/askplivo':
            return api.error('Invalid command')
        question = request.form['text']
        response_url = request.form['response_url']
    except KeyError:
        return api.error('Invalid request, no question provided')

    api.log.info('Received request',
             user_name=user_name, team_domain=team_domain,
             question=question, response_url=response_url)


    question = question.strip()
    if not question:
        return api.error('Invalid request, no question provided (empty)')

    api.get_log().info('Processing the question ...', question=question, response_url=response_url)
    job = enqueue_question(ask_bot_async, api.get_api_id(), question, response_url)
    api.get_log().info('Started background job', job=job)
    return jsonify({
            "response_type": "in_channel",
            "text": f"*TicketID*: {api.get_api_id()}\n_Processing your question, please wait..._\n"
    }), 200

def ask_bot_async(api_id, question, response_url):
    api = APIResponse(api_id)
    bot = None
    try:
        api.get_log().info('Creating bot instance')
        bot = FAQBot()
        bot.set_debug(True)
        api.get_log().info('Created bot instance')
        result = bot.ask(question=question)
        api.get_log().info('Got result from bot')

        data = json.loads(result)
        if data['status'] == 'error':
            api.get_log().error(f"Oops, something went wrong: {data['error']}", **data)
            json_response = {
                "text": f"*TicketID*: {api.get_api_id()}\n*Question*: _{question}_\nOops, something went wrong: {data['error']}\n",
                "response_type": "in_channel"
            }
            api.get_log().info('Sending response to slack', response_url=response_url, json_response=json_response)
            r = requests.post(response_url, json=json_response)
            api.get_log().info('Sent response to slack', response_url=response_url, status_code=r.status_code)
            return
        elif data['status'] == 'success':
            stats = data['response']['stats']
            api.get_log().debug('Stats', stats=stats)
            # format code block for Slack
            _answer = data['response']['answer']
            answer = ''
            for line in _answer.split('\n'):
                if line.startswith('```'):
                    answer += line[:3] + '\n'
                else:
                    answer += line + '\n'
            # format sources for Slack
            sources = '\n'.join(' - '+ src for src in data['response']['sources'])
            # send response to slack
            json_response = {
                "text": f"*TicketID*: {api.get_api_id()}\n*Question*: _{question}_\n*Answer*\n{answer}\n*Sources*\n{sources}\n",
                "response_type": "in_channel"
            }
            api.get_log().info('Sending response to slack', response_url=response_url, json_response=json_response)
            r = requests.post(response_url, json=json_response)
            api.get_log().info('Sent response to slack', response_url=response_url, status_code=r.status_code)
            return
    except Exception as e:
        api.get_log().error('Oops, something went wrong', error=str(e), trace=traceback.format_exc())
        json_response = {"text": f"*TicketID*: {api.get_api_id()}\n*Question*: _{question}_\n*Answer*\nOops, something went wrong\n", "response_type": "in_channel"}
        api.get_log().info('Sending response to slack', response_url=response_url, json_response=json_response)
        r = requests.post(response_url, json=json_response)
        api.get_log().info('Sent response to slack', response_url=response_url, status_code=r.status_code)
        return
    finally:
        try: del bot
        except: pass

    api.get_log().error('Oops, something went wrong', error='Unknown error')
    json_response = {"text": f"*TicketID*: {api.get_api_id()}\n*Question*: _{question}_\n*Answer*\nOops, something went wrong\n", "response_type": "in_channel"}
    api.get_log().info('Sending response to slack', response_url=response_url, json_response=json_response)
    r = requests.post(response_url, json=json_response)
    api.get_log().info('Sent response to slack', response_url=response_url, status_code=r.status_code)
    return



if __name__ == "__main__":
    app.run(debug=True)
