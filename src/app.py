from flask import Flask, request, jsonify, render_template
from query_translator import QueryTranslator
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize QueryTranslator with configuration
db_config = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': os.getenv('DB_PORT')
}

translator = QueryTranslator(
    db_config=db_config,
    api_key=os.getenv('GEMINI_API_KEY')
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def query():
    try:
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({
                'success': False,
                'error': 'No question provided'
            }), 400

        result = translator.process_question(data['question'])
        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True) 