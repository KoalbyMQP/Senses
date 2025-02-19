# Senses

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Setting Up the Virtual Environment](#setting-up-the-virtual-environment)
- [Running the Demos](#running-the-demos)
  - [Gripper Swap Demo](#gripper-swap-demo)
  - [Computer Vision Demo](#computer-vision-demo)

---

## Prerequisites

Before you begin, ensure you have the following:

- **Hardware:**  
  - Raspberry Pi 5 with Raspberry Pi OS installed.
  - Another Raspberry Pi active and on the same network (referred to as **clientPI**) for the Gripper Swap demo.

- **Software:**  
  - Python 3.x (typically pre-installed on Raspberry Pi OS)
  - Git

- **Network:**  
  - Ensure your Raspberry Pi 5 is connected to a network unless testing offline capabilities.

- **Miscellaneous (optional):**
  - An OpenAI API key
  - An OpenRouter API key

---

## Initial Setup

1. **Clone the Repository**

   Open a terminal on your Raspberry Pi 5 and execute:

   ```bash
   git clone https://github.com/KoalbyMQP/Senses
   cd <repository-directory-path>
   ```

2. **Review the Repository Structure**

   Familiarize yourself with the directory layout. Key files include:
   - `hostPi.py`: Script for the Gripper Swap demo.
   - `voice_helper.sh`: Script for the Computer Vision demo.

---

## Setting Up the Virtual Environment

1. **Create the Virtual Environment**

   ```bash
   python3 -m venv myvirtual
   ```

2. **Activate the Virtual Environment**

   ```bash
   source myvirtual/bin/activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

---

## Running the Demos

Both demos require the virtual environment to be active.

### Gripper Swap Demo

1. **Verify Client Device**

   - Ensure that the client Raspberry Pi is operational and on the same network as the host device.

2. **Launch the Demo**

   With the virtual environment activated, start the demo by running:

   ```bash
   python3 hostPi.py
   ```

   This will show you the IP address of the host device. Use the IP address to run the clientPi on the client device with:

   ```bash
   python3 clientPi.py --host-ip <host_ip>
   ```

### Computer Vision Demo

1. **Prepare the Script**

   Make the `voice_helper.sh` script executable:

   ```bash
   chmod +x voice_helper.sh
   ```

2. **Run the Script**

   Execute the demo with:

   ```bash
   ./voice_helper.sh
   ```
