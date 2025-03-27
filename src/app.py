from flask import Flask, render_template, request, jsonify
from query_translator import QueryTranslator
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Database configuration from environment variables
db_config = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST')
}

# Initialize QueryTranslator
translator = QueryTranslator(db_config, os.getenv('GOOGLE_API_KEY'))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def query():
    user_question = request.json.get('question')
    if not user_question:
        return jsonify({'error': 'No question provided'}), 400
    
    result = translator.process_question(user_question)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True) 