import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def test_api():
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("No API key found in environment variables")
        return

    try:
        # Configure the generative AI library
        genai.configure(api_key=api_key)
        
        # List available models
        print("Available models:")
        for m in genai.list_models():
            print(m.name)
        
        # Initialize the model - using an available model from the list
        model = genai.GenerativeModel('models/gemini-1.5-pro')
        
        print("\nTesting API connection...")
        response = model.generate_content("Say hello!")
        
        print("\nResponse:")
        print(response.text)
            
    except Exception as e:
        print("API test failed!")
        print("Error:", str(e))

if __name__ == "__main__":
    test_api() 