#!/bin/bash

TEMP_WARNING=70
TEMP_CRITICAL=85
CHECK_INTERVAL=5
TEMP_RISE_WARNING=2.0

VCGENCMD="/usr/bin/vcgencmd"

timestamp=$(date +%Y%m%d_%H%M%S)
LOG_DIR="logs_${timestamp}"
mkdir -p "${LOG_DIR}"/{pre_run,running,post_run,report}

get_metrics() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local cpu_temp=$(echo "scale=1; $(cat /sys/class/thermal/thermal_zone0/temp)/1000" | bc)
    local gpu_temp=$($VCGENCMD measure_temp | sed 's/temp=//' | sed 's/'"'"'C//')
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}')
    local mem_usage=$(free | grep Mem | awk '{printf "%.1f", ($3/$2) * 100}')
    local gpu_mem=$($VCGENCMD get_mem gpu | cut -d= -f2 | sed 's/M//')
    local cpu_freq=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq)
    local throttle=$($VCGENCMD get_throttled)
    
    echo "$timestamp,$cpu_temp,$gpu_temp,$cpu_usage,$mem_usage,$gpu_mem,$cpu_freq,$throttle"
}

monitor_phase() {
    local phase=$1
    local duration=$2
    local phase_dir="${LOG_DIR}/${phase}"
    local metrics_file="${phase_dir}/metrics.csv"
    
    echo "timestamp,cpu_temp,gpu_temp,cpu_usage,mem_usage,gpu_mem,cpu_freq,throttle" > "$metrics_file"
    
    if [ "$duration" -eq 0 ]; then
        while kill -0 $DEMO_PID 2>/dev/null; do
            get_metrics >> "$metrics_file"
            sleep $CHECK_INTERVAL
        done
    else
        local count=$((duration / CHECK_INTERVAL))
        for ((i=0; i<count; i++)); do
            get_metrics >> "$metrics_file"
            sleep $CHECK_INTERVAL
        done
    fi
}

check_plot_dependencies() {
    if ! command -v gnuplot &> /dev/null; then
        echo "gnuplot is not installed. Installing now..."
        sudo apt-get update && sudo apt-get install -y gnuplot
        if [ $? -ne 0 ]; then
            echo "Failed to install gnuplot. Plots will not be generated."
            return 1
        fi
    fi
    return 0
}

check_pdf_dependencies() {
    local missing_deps=()
    
    for dep in pandoc texlive-latex-base texlive-fonts-recommended texlive-fonts-extra texlive-latex-extra; do
        if ! dpkg -l | grep -q "^ii  $dep "; then
            missing_deps+=($dep)
        fi
    done
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo "Installing required dependencies for PDF generation..."
        sudo apt-get update && sudo apt-get install -y "${missing_deps[@]}"
        if [ $? -ne 0 ]; then
            echo "Failed to install dependencies. PDF report will not be generated."
            return 1
        fi
    fi
    return 0
}

generate_plots() {
    if ! check_plot_dependencies; then
        echo "gnuplot could not be found, please install it to generate plots"
        exit 1
    fi
    cat > "${LOG_DIR}/report/plots.gnu" << EOL
set terminal pngcairo size 1200,800 enhanced font 'Arial,10'
set output '${LOG_DIR}/report/system_metrics.png'

set multiplot layout 3,2 title "System Metrics Analysis"
set grid
set key outside
set xdata time
set timefmt "%Y-%m-%d %H:%M:%S"
set format x "%H:%M:%S"

set title "Temperature Metrics"
set ylabel "Temperature (°C)"
plot '${LOG_DIR}/pre_run/metrics.csv' using 1:2 title 'CPU Temp (Pre)' with lines, \
     '${LOG_DIR}/running/metrics.csv' using 1:2 title 'CPU Temp (Run)' with lines, \
     '${LOG_DIR}/post_run/metrics.csv' using 1:2 title 'CPU Temp (Post)' with lines, \
     '${LOG_DIR}/running/metrics.csv' using 1:3 title 'GPU Temp' with lines

set title "CPU Performance"
set ylabel "Usage (%)"
plot '${LOG_DIR}/running/metrics.csv' using 1:4 title 'CPU Usage' with lines

set title "Memory Utilization"
set ylabel "Usage (%)"
plot '${LOG_DIR}/running/metrics.csv' using 1:5 title 'RAM Usage' with lines, \
     '${LOG_DIR}/running/metrics.csv' using 1:6 title 'GPU Memory' with lines

set title "CPU Frequency"
set ylabel "Frequency (MHz)"
plot '${LOG_DIR}/running/metrics.csv' using 1:7 title 'CPU Freq' with lines

set title "System Status"
set ylabel "Throttle Status"
plot '${LOG_DIR}/running/metrics.csv' using 1:8 title 'Throttle' with lines

unset multiplot
EOL

    gnuplot "${LOG_DIR}/report/plots.gnu"
}

generate_report() {
    local report_file="${LOG_DIR}/report/summary.txt"
    
    {
        echo "=== DepthAI Performance Summary ==="
        echo "Run Date: $(date)"
        echo
        
        echo "=== Temperature Statistics ==="
        for phase in pre_run running post_run; do
            echo "${phase} phase:"
            echo "- Average CPU Temperature: $(awk -F',' 'NR>1 {sum+=$2; count++} END {printf "%.1f°C\n", (count>0)?sum/count:0}' ${LOG_DIR}/${phase}/metrics.csv)"
            echo "- Average GPU Temperature: $(awk -F',' 'NR>1 {sum+=$3; count++} END {printf "%.1f°C\n", (count>0)?sum/count:0}' ${LOG_DIR}/${phase}/metrics.csv)"
            echo "- Peak CPU Temperature: $(awk -F',' 'BEGIN {max=0} NR>1 {if($2>max)max=$2} END {printf "%.1f°C\n", max}' ${LOG_DIR}/${phase}/metrics.csv)"
            echo "- Peak GPU Temperature: $(awk -F',' 'BEGIN {max=0} NR>1 {if($3>max)max=$3} END {printf "%.1f°C\n", max}' ${LOG_DIR}/${phase}/metrics.csv)"
            echo
        done
        
        echo "=== Resource Usage (During Running Phase) ==="
        echo "CPU Usage:"
        echo "$(awk -F',' '
            BEGIN {max=0; min=100}
            NR>1 {
                sum+=$4; count++
                if($4>max) max=$4
                if($4<min) min=$4
            }
            END {
                printf "- Average: %.1f%%\n", (count>0)?sum/count:0
                printf "- Peak: %.1f%%\n", max
                printf "- Minimum: %.1f%%\n", min
            }
        ' ${LOG_DIR}/running/metrics.csv)"
        
        echo -e "\nMemory Usage:"
        echo "$(awk -F',' '
            BEGIN {max=0; min=100}
            NR>1 {
                sum+=$5; count++
                if($5>max) max=$5
                if($5<min) min=$5
            }
            END {
                printf "- Average: %.1f%%\n", (count>0)?sum/count:0
                printf "- Peak: %.1f%%\n", max
                printf "- Minimum: %.1f%%\n", min
            }
        ' ${LOG_DIR}/running/metrics.csv)"
        
        echo -e "\nGPU Memory:"
        echo "$(awk -F',' '
            BEGIN {max=0; min=999999}
            NR>1 {
                sum+=$6; count++
                if($6>max) max=$6
                if($6<min) min=$6
            }
            END {
                printf "- Average: %.1f MB\n", (count>0)?sum/count:0
                printf "- Peak: %.1f MB\n", max
                printf "- Minimum: %.1f MB\n", min
            }
        ' ${LOG_DIR}/running/metrics.csv)"
        
        echo -e "\nCPU Frequency Analysis:"
        echo "$(awk -F',' '
            NR>1 {
                sum+=$7; count++
                if($7>max) max=$7
                if(NR==2 || $7<min) min=$7
            }
            END {
                printf "- Average: %.0f MHz\n", sum/count
                printf "- Peak: %.0f MHz\n", max
                printf "- Minimum: %.0f MHz\n", min
            }
        ' ${LOG_DIR}/running/metrics.csv)"
        
        echo -e "\n=== Performance Warnings ==="
        awk -F',' '
            NR>1 {
                if ($2 >= 70) printf "WARNING: High CPU temperature (%.1f°C) at %s\n", $2, $1
                if ($4 >= 80) printf "WARNING: High CPU usage (%.1f%%) at %s\n", $4, $1
                if ($5 >= 90) printf "WARNING: High memory usage (%.1f%%) at %s\n", $5, $1
            }
        ' ${LOG_DIR}/running/metrics.csv
        
        echo -e "\nDetailed metrics and graphs available in: ${LOG_DIR}/report/"
        
    } > "$report_file"
}

generate_pdf_report() {
    local report_dir="${LOG_DIR}/report"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    if ! check_pdf_dependencies; then
        echo "Skipping PDF generation due to missing dependencies"
        return 1
    fi
    
    # Create markdown content
    cat > "${report_dir}/report.md" << EOL
---
title: "DepthAI Performance Report"
date: "${timestamp}"
geometry: margin=1in
colorlinks: true
header-includes: |
    \\usepackage{fancyhdr}
    \\pagestyle{fancy}
    \\fancyhead[L]{DepthAI Report}
    \\fancyhead[R]{Generated on ${timestamp}}
---

# Executive Summary

This report presents the performance analysis of the DepthAI system during a monitoring session.

## System Overview

- **Test Duration**: $(( ($(date +%s) - $(date -d "$(head -n 2 ${LOG_DIR}/pre_run/metrics.csv | tail -n 1 | cut -d',' -f1)" +%s) ) )) seconds
- **Device Type**: $(python3 -c "import depthai as dai; d=dai.Device(); print(d.getDeviceName()); d.close()" 2>/dev/null || echo "Unknown")
- **SDK Version**: $(python3 -c "import depthai as dai; print(dai.__version__)" 2>/dev/null || echo "Unknown")

## Temperature Analysis

![Temperature Metrics](system_metrics.png)

### Temperature Statistics

$(awk -F',' '
    NR>1 {
        cpu_sum+=$2; gpu_sum+=$3; count++
        if($2>cpu_max) cpu_max=$2
        if($3>gpu_max) gpu_max=$3
    }
    END {
        printf "| Metric | Average | Peak |\n"
        printf "|--------|---------|------|\n"
        printf "| CPU Temperature | %.1f°C | %.1f°C |\n", cpu_sum/count, cpu_max
        printf "| GPU Temperature | %.1f°C | %.1f°C |\n", gpu_sum/count, gpu_max
    }
' ${LOG_DIR}/running/metrics.csv)

## Resource Utilization

### CPU and Memory Usage

$(awk -F',' '
    NR>1 {
        cpu_sum+=$4; mem_sum+=$5; count++
        if($4>cpu_max) cpu_max=$4
        if($5>mem_max) mem_max=$5
    }
    END {
        printf "| Resource | Average | Peak |\n"
        printf "|----------|---------|------|\n"
        printf "| CPU Usage | %.1f%% | %.1f%% |\n", cpu_sum/count, cpu_max
        printf "| Memory Usage | %.1f%% | %.1f%% |\n", mem_sum/count, mem_max
    }
' ${LOG_DIR}/running/metrics.csv)

## Performance Alerts

$(awk -F',' '
    BEGIN {
        printf "| Time | Event | Value |\n"
        printf "|------|-------|-------|\n"
    }
    NR>1 && $2>70 {
        printf "| %s | High CPU Temperature | %.1f°C |\n", $1, $2
    }
    NR>1 && $4>80 {
        printf "| %s | High CPU Usage | %.1f%% |\n", $1, $4
    }
' ${LOG_DIR}/running/metrics.csv)

## System Logs

\`\`\`
$(tail -n 20 "${LOG_DIR}/running/depthai.log")
\`\`\`

## Recommendations

$(if awk -F',' 'NR>1 && $2>70 {exit 1}' ${LOG_DIR}/running/metrics.csv; then
    echo "- System temperatures remained within acceptable ranges"
else
    echo "- Consider improving system cooling as temperatures exceeded 70°C"
fi)

$(if awk -F',' 'NR>1 && $4>80 {exit 1}' ${LOG_DIR}/running/metrics.csv; then
    echo "- CPU usage was within normal parameters"
else
    echo "- High CPU usage detected - consider optimizing workload"
fi)

EOL

    # Convert markdown to PDF using pandoc
    cd "${report_dir}"
    pandoc -f markdown -t pdf \
        --pdf-engine=xelatex \
        --variable mainfont="DejaVu Sans" \
        --variable monofont="DejaVu Sans Mono" \
        --toc \
        --highlight-style=tango \
        -o "depthai_report.pdf" \
        "report.md"

    echo "PDF report generated at: ${report_dir}/depthai_report.pdf"
}

echo "Starting DepthAI monitoring..."

echo "Collecting pre-run metrics..."
monitor_phase "pre_run" 30

cd ~/vdepthai || exit 1
source bin/activate || exit 1
cd depthai || exit 1

echo "Starting DepthAI..."
python3 depthai_demo.py -cnn yolo-v3-tiny-tf 2>&1 | tee "${LOG_DIR}/running/depthai.log" &
DEMO_PID=$!

monitor_phase "running" 0

echo "Collecting post-run metrics..."
monitor_phase "post_run" 30

echo "Generating reports..."
generate_plots
generate_report
generate_pdf_report

echo "Monitoring completed. Reports available in: ${LOG_DIR}"
echo "Summary report: ${LOG_DIR}/report/summary.txt"
echo "System metrics plot: ${LOG_DIR}/report/system_metrics.png"
echo "PDF report: ${LOG_DIR}/report/depthai_report.pdf"