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
        
        # Print API version
        print(f"API Version: {genai.__version__}")
        
        # List available models
        models = genai.list_models()
        print("\nAvailable models:")
        for m in models:
            print(f"Name: {m.name}")
            print(f"Display Name: {m.display_name}")
            print(f"Supported Generation Methods: {m.supported_generation_methods}")
            print("---")
        
        # Initialize the model using the base model name
        model = genai.GenerativeModel('models/gemini-1.5-pro')
        
        print("\nTesting API connection...")
        chat = model.start_chat()  # Start a chat session
        response = chat.send_message("Say hello!")
        
        print("\nResponse:")
        print(response.text)
            
    except Exception as e:
        print("API test failed!")
        print("Error:", str(e))
        print(f"Error type: {type(e)}")

if __name__ == "__main__":
    test_api() 