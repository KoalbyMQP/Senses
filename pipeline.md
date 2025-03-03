# Robotic Gripper Swap System – Pipeline Overview

---

## 1. Host Pi (hostPi.py)

- **Responsibilities:**
  - Retrieve and display the Host Pi’s IP address.
  - Show available gripper options.
  - Check for internet connectivity:
    - **If offline:**  
      - Play a TTS warning (using `espeak`) notifying the user about the lack of internet.
      - Loop and repeat the warning every minute, without initializing ZeroMQ sockets or launching subprocesses.
    - **If online:**  
      - Set up ZeroMQ communication:
        - Create a SUB socket to receive commands from the voice detection module.
        - Create a PUB socket to forward commands to the Client Pi.
  - Launch two subprocesses in new terminals:
    - **Voice Detection Process:** Runs `gripperswapVoiceDetection.py` (responsible for capturing and processing voice commands).
    - **Confirmation Listener:** Runs `confirmationListener.py` (which listens for and logs confirmation messages from the Client Pi).

- **Message Flow:**
  - Receives the `SWAP` command (with a timestamp) from the voice detection module.
  - Appends its own receipt timestamp and forwards the full message to the Client Pi.

---

## 2. Gripper Swap Voice Detection (gripperswapVoiceDetection.py)

- **Initialization & Environment Setup:**
  - **.env Check:**  
    - On startup, the module checks for a `.env` file.
    - If not found, it creates one with placeholder keys for `OPENAI_API_KEY` and `OPENROUTER_API_KEY` and prompts the user for confirmation.  
    - The keys are then loaded using `dotenv`; if keys remain unset, the program proceeds as normal but would fail at the steps that require API keys and will go for fallback checks.

- **Audio Capture & Transcription:**
  - Uses Python’s `speech_recognition` to capture audio from a microphone.
  - **Transcription:**  
    - Attempts to call the OpenAI Whisper API (via `_transcribe_with_api()`) using the provided `OPENAI_API_KEY`.
    - **Fallback:** If the API call fails or no key is found, the system falls back to using Google Speech Recognition.

- **Command Parsing & Auditing:**
  - The transcribed text is passed to `parse_command()`, which:
    - Recognizes direct numeric commands or maps spoken gripper names (e.g., “thermometer gripper”) to a gripper number.
  - **Auditing:**  
    - If parsing fails, `_audit_command()` is invoked:
      - It first tries an OpenAI-based auditing call (using model `o3-mini`).
      - If that fails, it falls back to an OpenRouter API (for example model `anthropic/claude-3-5-sonnet`).
      - If API keys work, it will send a message to the LLM to audit the command using a custom prompt that can be changed (the llm could predicts issues from speech recognition like "swamp gripper 3" and still return 3)
      - The auditing returns only a valid gripper number (1-10) or “cant evaluate reliably”
    - If no API keys are found for OpenAI or OpenRouter, the system skips auditing.
  
- **Command Dispatch & Feedback:**
  - Once validated, the command is sent via ZeroMQ using the SpeechHandler.
  - A TTS confirmation is played:
    - **TTS Processing:**  
      - The system calls `play_tts()`, which attempts to use the OpenAI TTS API (model `"tts-1-hd"` with voice `"sage"`).
      - **Fallback:** If that API call fails, it falls back to using Google TTS.
  
- **Confirmation Listener Method:**
  - Contains a method (`listen_for_confirmation()`) that non-blockingly listens on its ZeroMQ SUB socket for confirmation messages from the Confirmation Listener.

---

## 3. Client Pi (clientPi.py)

- **Responsibilities:**
  - Receives the `SWAP` command forwarded by the Host Pi.
  - **Processing:**
    - Parses the message, which contains the gripper ID and timestamps.
    - If the requested gripper differs from the currently active one, instructs the hardware (e.g., via an Arduino serial connection) to perform the swap.
  - **Confirmation:**
    - Sends a confirmation message back through ZeroMQ. This message includes details such as:
      - The new current gripper and previous gripper.
      - Timestamps for voice command sending, host forwarding, client receipt, processing duration, etc.

---

## 4. Confirmation Listener (confirmationListener.py)

- **Responsibilities:**
  - Listens on a dedicated ZeroMQ port for confirmation messages sent from the Client Pi.
  - **Processing:**
    - Decodes and splits the confirmation message.
    - Calculates latencies (e.g., voice-to-host, host-to-client, processing time).
    - Logs detailed status messages (e.g., “Swap successful” or “Gripper already active”).
  - May also trigger additional TTS feedback based on the confirmation.

---

## Fallback Checks and API Usage

- **Transcription:**
  - **Primary:** OpenAI Whisper API (using `OPENAI_API_KEY`).
  - **Fallback:** Google Speech Recognition if API call fails or keys are missing.
  
- **Text-to-Speech (TTS):**
  - **Primary:** OpenAI TTS API (using model `"tts-1-hd"` and voice `"sage"`, with `OPENAI_API_KEY`).
  - **Fallback:** Google TTS via gTTS if the API call fails or keys are not provided.
  
- **Auditing:**
  - **Primary:** OpenAI-based auditing (using model `"o3-mini"`).
  - **Fallback:** OpenRouter API (using model `"anthropic/claude-3-5-sonnet"`) if the primary fails.
  - **Skipping:** If no API keys are found for OpenAI or OpenRouter, the system skips auditing.

- **Environment Setup:**
  - Checks for a `.env` file at startup.  
  - If missing, creates one with placeholder values and prompts the user to confirm key entry.  
  - Even if keys are missing, fallback mechanisms ensure the system remains operational.

---
