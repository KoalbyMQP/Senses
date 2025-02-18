import os
import requests
from Speech.config import initialize_api_keys

initialize_api_keys()

def audit_command(text, audit_prompt, valid_check, openrouter_title):
    """
    A generic auditing function. It performs an audit of the input text via:
    
      1. OpenAI's chat completions (if OPENAI_API_KEY is set); and if that fails,
      2. OpenRouter's chat completions (if OPENROUTER_API_KEY is set).
      
    Parameters:
      text (str): The text to audit.
      audit_prompt (str): The prompt to guide auditing.
      valid_check (callable): A function that takes the audited text and returns True if it meets the criteria.
      openrouter_title (str): The title to use in the OpenRouter header.

    Returns:
      str: The audited text (if valid) or the original text.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            response = requests.post(
                url="https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}"},
                json={
                    "model": "o3-mini",
                    "messages": [
                        {"role": "system", "content": audit_prompt},
                        {"role": "user", "content": text}
                    ],
                    "temperature": 0.1
                },
                timeout=3
            )
            audited_text = response.json()['choices'][0]['message']['content'].strip()
            if valid_check(audited_text):
                return audited_text
        except Exception as e:
            print(f"OpenAI Audit error: {e}")
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_api_key:
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_api_key}",
                    "HTTP-Referer": "http://localhost/",
                    "X-Title": openrouter_title
                },
                json={
                    "model": "deepseek/deepseek-r1-distill-llama-70b:free",
                    "messages": [
                        {"role": "system", "content": audit_prompt},
                        {"role": "user", "content": text}
                    ],
                    "temperature": 0.1
                },
                timeout=3
            )
            audited_text = response.json()['choices'][0]['message']['content'].strip()
            if valid_check(audited_text):
                return audited_text
        except Exception as e:
            print(f"OpenRouter Audit error: {e}")
    print("Auditing failed, skipping auditing.")
    return text
