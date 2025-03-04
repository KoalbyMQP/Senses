import os
import json
import logging
import time
from openai import OpenAI
from Speech.config import initialize_api_keys

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

initialize_api_keys()

def audit_command(text, audit_prompt, valid_check, openrouter_title, max_retries=2):
    """
    Audits a command text using OpenAI or OpenRouter API.
    
    Args:
        text (str): The text to audit.
        audit_prompt (str): The system prompt to use for auditing.
        valid_check (callable): A function that checks if the audited text is valid.
        openrouter_title (str): The title to use for OpenRouter API.
        max_retries (int, optional): Maximum number of retries. Defaults to 2.
        
    Returns:
      str: The audited text (if valid) or the original text.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and openai_key != "YOUR_OPENAI_KEY":
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Sending request to OpenAI API: {text}")
                client = OpenAI(api_key=openai_key)
                
                completion = client.chat.completions.create(
                    model="gpt-4o-realtime-preview-2024-12-17", 
                    messages=[
                        {"role": "system", "content": audit_prompt},
                        {"role": "user", "content": text}
                    ],
                    temperature=0,
                )
                
                # Get response content
                audited_text = completion.choices[0].message.content.strip()
                logger.info(f"Audited text: {audited_text}")
                
                if valid_check(audited_text):
                    return audited_text
                else:
                    logger.warning(f"Audited text failed validation: {audited_text}")
                    
            except Exception as e:
                logger.error(f"Error with OpenAI API on attempt {attempt+1}/{max_retries+1}: {str(e)}")
                if attempt < max_retries:
                    time.sleep(1)  # Wait before retry
                continue
                
    # Fallback to OpenRouter if OpenAI failed or API key not available
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_api_key and openrouter_api_key != "YOUR_OPENROUTER_KEY":
        try:
            logger.info(f"Falling back to OpenRouter API: {text}")
            
            # Method 1: Using OpenAI client with OpenRouter base URL
            try:
                client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=openrouter_api_key,
                )
                
                completion = client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": "http://localhost/",
                        "X-Title": openrouter_title,
                    },
                    model= "google/gemini-2.0-flash-exp:free",  
                    messages=[
                        {"role": "system", "content": audit_prompt},
                        {"role": "user", "content": text}
                    ],
                    temperature=0.1
                )
                
                audited_text = completion.choices[0].message.content.strip()
                logger.info(f"OpenRouter audited text: {audited_text}")
                if valid_check(audited_text):
                    return audited_text
                    
            except Exception as e:
                logger.error(f"Error with OpenRouter using OpenAI client: {str(e)}")
                
                # Method 2: Fallback to using direct requests if client approach fails
                import requests
                
                response = requests.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openrouter_api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://localhost/",
                        "X-Title": openrouter_title
                    },
                    json={
                        "model": "google/gemini-2.0-flash-exp:free",  # Using lower-cost fallback
                        "messages": [
                            {"role": "system", "content": audit_prompt},
                            {"role": "user", "content": text}
                        ],
                        "temperature": 0.1
                    },
                    timeout=3
                )
                
                response.raise_for_status()
                
                # Log response for debugging
                response_json = response.json()
                logger.debug(f"OpenRouter API response: {json.dumps(response_json, indent=2)}")
                
                # Check if response has expected structure
                if 'choices' in response_json and len(response_json['choices']) > 0:
                    if 'message' in response_json['choices'][0] and 'content' in response_json['choices'][0]['message']:
                        audited_text = response_json['choices'][0]['message']['content'].strip()
                        logger.info(f"OpenRouter audited text (fallback): {audited_text}")
                        if valid_check(audited_text):
                            return audited_text
                    else:
                        logger.error(f"Unexpected OpenRouter response structure: {response_json}")
                else:
                    logger.error(f"No 'choices' in OpenRouter response: {response_json}")
                    
        except Exception as e:
            logger.error(f"Error with OpenRouter API: {str(e)}")
    
    # If all else fails, return the original text
    logger.warning("All API attempts failed, returning original text")
    return text
