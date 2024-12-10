import jinja2
import subprocess
from pathlib import Path
from ..config.settings import Settings

class LaTeXHandler:
    def __init__(self):
        self.settings = Settings()
        template_path = Path(__file__).parent.parent / 'templates' / 'report_template.tex'
        with open(template_path, 'r') as f:
            self.template = f.read()

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
