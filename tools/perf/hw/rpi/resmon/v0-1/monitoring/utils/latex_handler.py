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
{\Large Generated on: {{date}}\par}
\vspace{3cm}
{\large\textbf{Total Duration:} {{duration}} seconds\par}
\vspace{0.5cm}
{\large\textbf{Pre-run Duration:} {{pre_duration}} seconds\par}
{\large\textbf{Runtime Duration:} {{runtime_duration}} seconds\par}
{\large\textbf{Post-run Duration:} {{post_duration}} seconds\par}
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

{{detailed_metrics}}

\section{Performance Analysis}
\subsection{Key Findings}
\begin{itemize}
{{analysis_points}}
\end{itemize}

\section{Recommendations}
\begin{itemize}
{{recommendations}}
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
        
        # Calculate runtime duration
        runtime_duration = data['duration'] - (data['pre_duration'] + data['post_duration'])
        
        # Create context dictionary for template
        context = {
            'date': data['date'],
            'duration': f"{data['duration']:.1f}",
            'pre_duration': str(data['pre_duration']),
            'runtime_duration': f"{runtime_duration:.1f}",
            'post_duration': str(data['post_duration']),
            'detailed_metrics': detailed_metrics,
            'analysis_points': analysis_points,
            'recommendations': recommendations
        }
        
        # Use proper template rendering
        template = jinja2.Template(self.template)
        tex_content = template.render(**context)
        
        tex_path = output_path.with_suffix('.tex')
        with open(tex_path, 'w') as f:
            f.write(tex_content)
        
        for _ in range(2):  
            subprocess.run(['pdflatex', '-interaction=nonstopmode', str(tex_path)], 
                          cwd=output_path.parent,
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL)