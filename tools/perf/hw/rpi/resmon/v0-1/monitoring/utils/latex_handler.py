import jinja2
import subprocess
from pathlib import Path

class LaTeXHandler:
    def __init__(self):
        self.template = r"""
\documentclass[11pt]{article}
\usepackage[a4paper,margin=1in]{geometry}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{xcolor}
\usepackage{fancyhdr}
\usepackage{float}
\usepackage{titlesec}
\usepackage{enumitem}

\definecolor{sectioncolor}{RGB}{70,130,180}

\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{1pt}
\fancyhead[L]{DepthAI Monitoring}
\fancyhead[R]{\today}
\fancyfoot[C]{\thepage}

\titleformat{\section}
{\color{sectioncolor}\normalfont\Large\bfseries}
{\thesection}{1em}{}

\begin{document}

\begin{titlepage}
\centering
\vspace*{2cm}
{\Huge\bfseries DepthAI Performance Report\par}
\vspace{2cm}
{\Large Generated on: \VAR{date}\par}
\vspace{3cm}
{\large\textbf{Monitoring Duration:} \VAR{duration} seconds\par}
\vspace{0.5cm}
{\large\textbf{Pre-run Duration:} \VAR{pre_duration} seconds\par}
{\large\textbf{Runtime Duration:} \VAR{runtime_duration} seconds\par}
{\large\textbf{Post-run Duration:} \VAR{post_duration} seconds\par}
\end{titlepage}

\section{System Performance Overview}

\subsection{Temperature Analysis}
\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{system_temperature.png}
\caption{CPU and GPU Temperature Trends}
\end{figure}

\subsection{Resource Utilization}
\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{resource_usage.png}
\caption{Memory Usage Patterns}
\end{figure}

\begin{figure}[H]
\centering
\includegraphics[width=\textwidth]{cpu_metrics.png}
\caption{CPU Usage Analysis}
\end{figure}

\section{Detailed Metrics}

\VAR{detailed_metrics}

\section{Performance Analysis}
\subsection{Key Findings}
\begin{itemize}
\VAR{analysis_points}
\end{itemize}

\section{Recommendations}
\begin{itemize}
\VAR{recommendations}
\end{itemize}

\end{document}
"""

    def _format_metrics_table(self, metrics_data):
        table = []
        for metric in metrics_data:
            table.append(f"""
\\subsection{{{metric['name']}}}
\\begin{{tabular}}{{lr}}
\\toprule
Statistic & Value \\\\
\\midrule
Mean & {metric['mean']} \\\\
Maximum & {metric['max']} \\\\
Minimum & {metric['min']} \\\\
\\bottomrule
\\end{{tabular}}
""")
        return '\n'.join(table)

    def generate_pdf(self, data: dict, output_path: Path):
        detailed_metrics = self._format_metrics_table(data['metrics'])
        
        analysis_points = '\n'.join([f"\\item {point}" for point in data['analysis'].split('\n')])
        
        recommendations = []
        if 'CPU' in data['analysis']:
            recommendations.append("Consider optimizing CPU-intensive operations")
        if 'Memory' in data['analysis']:
            recommendations.append("Monitor memory usage patterns and implement cleanup")
        if 'temperature' in data['analysis']:
            recommendations.append("Review cooling system and resource usage")
        
        recommendations = '\n'.join([f"\\item {rec}" for rec in recommendations])
        
        tex_content = self.template.replace('\\VAR{date}', data['date'])
        tex_content = tex_content.replace('\\VAR{duration}', str(int(data['duration'])))
        tex_content = tex_content.replace('\\VAR{pre_duration}', str(data['pre_duration']))
        tex_content = tex_content.replace('\\VAR{post_duration}', str(data['post_duration']))
        tex_content = tex_content.replace('\\VAR{detailed_metrics}', detailed_metrics)
        tex_content = tex_content.replace('\\VAR{analysis_points}', analysis_points)
        tex_content = tex_content.replace('\\VAR{recommendations}', recommendations)
        
        tex_path = output_path.with_suffix('.tex')
        with open(tex_path, 'w') as f:
            f.write(tex_content)
        
        for _ in range(2):  
            subprocess.run(['pdflatex', '-interaction=nonstopmode', str(tex_path)], 
                         cwd=output_path.parent,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)