import os
from dotenv import load_dotenv

def initialize_api_keys():
    """
    Checks for a .env file in the Speech directory. If not found,
    creates one with placeholder API keys and prompts the user to update them.
    Then, loads the environment variables.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(current_dir, ".env")
    
    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            f.write("OPENAI_API_KEY=YOUR_OPENAI_KEY\n")
            f.write("OPENROUTER_API_KEY=YOUR_OPENROUTER_KEY\n")
        print("No .env file found. Created one with placeholder API keys at:")
        print(env_path)
        input("Please update the API keys in the .env file if desired and then press Enter to continue...")
    
    load_dotenv(env_path)
    
    openai_key = os.getenv("OPENAI_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    
    if not openai_key or openai_key == "YOUR_OPENAI_KEY":
        print("Warning: OPENAI_API_KEY is not set or still using a placeholder. Falling back to alternative methods where necessary.")
    if not openrouter_key or openrouter_key == "YOUR_OPENROUTER_KEY":
        print("Warning: OPENROUTER_API_KEY is not set or still using a placeholder. Auditing features may be limited.") 