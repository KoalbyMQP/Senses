#!/bin/bash

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$(dirname "$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")")")")")"

# Activate virtual environment
cd ~/vdepthai || exit 1
source bin/activate || exit 1

check_python_package() {
    python3 -c "import $1" &>/dev/null
    return $?
}

check_system_package() {
    dpkg -l "$1" &>/dev/null
    return $?
}

# Install Python dependencies
PYTHON_PACKAGES=("psutil" "pandas" "matplotlib" "click" "pyyaml" "jinja2")
for package in "${PYTHON_PACKAGES[@]}"; do
    if check_python_package "$package"; then
        echo "✓ $package already installed"
    else
        echo "Installing $package..."
        pip install "$package"
        if [ $? -eq 0 ]; then
            echo "✓ Successfully installed $package"
        else
            echo "✗ Failed to install $package"
            exit 1
        fi
    fi
done

# Install LaTeX dependencies
LATEX_PACKAGES=("texlive-latex-base" "texlive-latex-extra" "texlive-fonts-recommended")
NEED_APT_UPDATE=false

for package in "${LATEX_PACKAGES[@]}"; do
    if check_system_package "$package"; then
        echo "✓ $package already installed"
    else
        NEED_APT_UPDATE=true
        break
    fi
done

if [ "$NEED_APT_UPDATE" = true ]; then
    echo "Updating package lists..."
    sudo apt-get update
    if [ $? -ne 0 ]; then
        echo "✗ Failed to update package lists"
        exit 1
    fi

    for package in "${LATEX_PACKAGES[@]}"; do
        if ! check_system_package "$package"; then
            echo "Installing $package..."
            sudo apt-get install -y "$package"
            if [ $? -eq 0 ]; then
                echo "✓ Successfully installed $package"
            else
                echo "✗ Failed to install $package"
                exit 1
            fi
        fi
    done
fi

# Create desktop shortcut
cat > ~/Desktop/depthai-monitor.desktop << EOL
[Desktop Entry]
Name=DepthAI Monitor
Exec=bash -c 'lxterminal --working-directory=/home/finley/Documents/GitHub/RaspberryPi-Code_24-25/test/io/inputs/camera/oak-d-lite/vdepthai -e "bash -c \"source bin/activate && cd /home/finley/Documents/GitHub/RaspberryPi-Code_24-25/tools/perf/hw/rpi/resmon/v0-1/monitoring/ && chmod +x run_monitor.sh && ./run_monitor.sh; exec bash\""'
Type=Application
Terminal=false
Categories=Development;
Icon=utilities-terminal
EOL

# Make the desktop entry executable
chmod +x ~/Desktop/depthai-monitor.desktop

# Deactivate virtual environment
deactivate

echo "✓ Installation completed successfully"
