import os
import requests
import time
import json
import logging
from Speech.config import initialize_api_keys

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

initialize_api_keys()

def audit_command(text, audit_prompt, valid_check, openrouter_title, max_retries=2):
    """
    A generic auditing function. It performs an audit of the input text via:
    
      1. OpenAI's chat completions (if OPENAI_API_KEY is set); and if that fails,
      2. OpenRouter's chat completions (if OPENROUTER_API_KEY is set).
      
    Parameters:
      text (str): The text to audit.
      audit_prompt (str): The prompt to guide auditing.
      valid_check (callable): A function that takes the audited text and returns True if it meets the criteria.
      openrouter_title (str): The title to use in the OpenRouter header.
      max_retries (int): Maximum number of retry attempts for transient errors.

    Returns:
      str: The audited text (if valid) or the original text.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Sending request to OpenAI API: {text}")
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
                
                response.raise_for_status()
                
                # Log response for debugging
                response_json = response.json()
                logger.debug(f"OpenAI API response: {json.dumps(response_json, indent=2)}")
                
                # Check if response has expected structure
                if 'choices' in response_json and len(response_json['choices']) > 0:
                    if 'message' in response_json['choices'][0] and 'content' in response_json['choices'][0]['message']:
                        audited_text = response_json['choices'][0]['message']['content'].strip()
                        logger.info(f"Audited text: {audited_text}")
                        if valid_check(audited_text):
                            return audited_text
                    else:
                        logger.error(f"Unexpected response structure: {response_json}")
                else:
                    logger.error(f"No 'choices' in response: {response_json}")
                
                break  # Break if we got a response without error
                
            except requests.exceptions.HTTPError as e:
                error_msg = f"OpenAI API HTTP error: {e}"
                try:
                    error_json = response.json()
                    error_msg += f" - Response: {json.dumps(error_json, indent=2)}"
                except:
                    error_msg += f" - Response text: {response.text}"
                logger.error(error_msg)
                break  # Break on HTTP errors, as retrying is unlikely to help
                
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                # Only retry on network errors
                logger.warning(f"OpenAI API network error (attempt {attempt+1}/{max_retries+1}): {e}")
                if attempt < max_retries:
                    # Exponential backoff
                    time.sleep(2 ** attempt)
                    continue
                logger.error(f"Max retries reached for OpenAI API")
                break
                
            except Exception as e:
                logger.error(f"OpenAI Audit error: {e}")
                break

    # Fallback to OpenRouter
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_api_key:
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Sending request to OpenRouter API: {text}")
                response = requests.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openrouter_api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://localhost/",
                        "X-Title": openrouter_title
                    },
                    json={
                        "model": "google/gemini-2.0-flash-exp:free",
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
                        logger.info(f"Audited text from OpenRouter: {audited_text}")
                        if valid_check(audited_text):
                            return audited_text
                    else:
                        logger.error(f"Unexpected OpenRouter response structure: {response_json}")
                else:
                    logger.error(f"No 'choices' in OpenRouter response: {response_json}")
                
                break  # Break if we got a response without error
                
            except requests.exceptions.HTTPError as e:
                error_msg = f"OpenRouter API HTTP error: {e}"
                try:
                    error_json = response.json()
                    error_msg += f" - Response: {json.dumps(error_json, indent=2)}"
                except:
                    error_msg += f" - Response text: {response.text}"
                logger.error(error_msg)
                break
                
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                # Only retry on network errors
                logger.warning(f"OpenRouter API network error (attempt {attempt+1}/{max_retries+1}): {e}")
                if attempt < max_retries:
                    # Exponential backoff
                    time.sleep(2 ** attempt)
                    continue
                logger.error(f"Max retries reached for OpenRouter API")
                break
                
            except Exception as e:
                logger.error(f"OpenRouter Audit error: {e}")
                break
    
    logger.warning("Auditing failed, skipping auditing.")
    return text