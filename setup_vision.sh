#!/bin/bash

export GDK_BACKEND=x11
export QT_QPA_PLATFORM=xcb
export DISPLAY=:0
export XDG_SESSION_TYPE=x11

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}===== Vision System Setup Script =====${NC}"

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

VISION_DIR="$SENSES_DIR/Vision"
if [ -d "$VISION_DIR" ]; then
    echo -e "${YELLOW}Navigating to $VISION_DIR...${NC}"
    cd "$VISION_DIR" || { echo -e "${RED}Failed to navigate to $VISION_DIR${NC}"; exit 1; }
else
    echo -e "${RED}Error: Vision directory not found in $SENSES_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}Starting Vision System...${NC}"
echo -e "${YELLOW}Running: python3 depthai_demo.py${NC}"
python3 depthai_demo.py -cnn yolo-v3-tiny-tf -s color "$@" || { echo -e "${RED}Failed to run depthai_demo.py${NC}"; exit 1; }

deactivate 