from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/')
def index():
    return 'Hello, Flask!'

@app.route('/api/echo', methods=['POST'])
def echo():
    data = request.json
    return jsonify({'you_sent': data})

@app.route('/api/add', methods=['POST'])
def add():
    data = request.json
    a = data.get('a', 0)
    b = data.get('b', 0)
    return jsonify({'result': a + b})

if __name__ == '__main__':
    app.run(debug=True)
