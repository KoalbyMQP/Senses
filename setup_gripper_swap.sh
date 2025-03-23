#!/bin/bash

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}===== Gripper Swap System Setup Script =====${NC}"

find_senses_dir() {
    common_locations=(
        "$HOME/Documents/GitHub/Senses"
        "$HOME/GitHub/Senses"
        "$HOME/Senses"
    )
    
    for loc in "${common_locations[@]}"; do
        if [ -d "$loc" ]; then
            echo "$loc"
            return 0
        fi
    done
    
    echo -e "${YELLOW}Searching for Senses directory (this may take a moment)...${NC}"
    found_dir=$(find $HOME -type d -name "Senses" -not -path "*/\.*" 2>/dev/null | head -n 1)
    
    if [ -n "$found_dir" ]; then
        echo "$found_dir"
        return 0
    fi
    
    echo ""
    return 1
}

SENSES_DIR=$(find_senses_dir)

if [ -z "$SENSES_DIR" ]; then
    echo -e "${RED}Error: Could not find the Senses directory.${NC}"
    echo -e "Please specify the path to your Senses directory: "
    read SENSES_DIR
    
    if [ ! -d "$SENSES_DIR" ]; then
        echo -e "${RED}Error: The specified directory does not exist.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}Found Senses directory at: ${SENSES_DIR}${NC}"

cd "$SENSES_DIR" || { echo -e "${RED}Failed to navigate to $SENSES_DIR${NC}"; exit 1; }

VENV_PATH="$SENSES_DIR/venv"
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv || { echo -e "${RED}Failed to create virtual environment${NC}"; exit 1; }
    echo -e "${GREEN}Virtual environment created successfully.${NC}"
else
    echo -e "${YELLOW}Virtual environment already exists.${NC}"
fi

echo -e "${YELLOW}Activating virtual environment...${NC}"
source "$VENV_PATH/bin/activate" || { echo -e "${RED}Failed to activate virtual environment${NC}"; exit 1; }

if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}Installing dependencies from requirements.txt...${NC}"
    pip install -r requirements.txt || { echo -e "${RED}Failed to install dependencies${NC}"; exit 1; }
    echo -e "${GREEN}Dependencies installed successfully.${NC}"
else
    echo -e "${RED}Warning: requirements.txt not found in $SENSES_DIR${NC}"
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Setup aborted.${NC}"
        exit 1
    fi
fi

GRIPPER_DIR="$SENSES_DIR/Gripper/swap"
if [ -d "$GRIPPER_DIR" ]; then
    echo -e "${YELLOW}Navigating to $GRIPPER_DIR...${NC}"
    cd "$GRIPPER_DIR" || { echo -e "${RED}Failed to navigate to $GRIPPER_DIR${NC}"; exit 1; }
else
    echo -e "${RED}Error: Gripper/swap directory not found in $SENSES_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}Starting Gripper Swap System...${NC}"
echo -e "${YELLOW}Running: python3 hostPi.py${NC}"
python3 hostPi.py || { echo -e "${RED}Failed to run hostPi.py${NC}"; exit 1; }

deactivate 