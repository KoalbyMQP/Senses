import click
from pathlib import Path
from datetime import datetime
from .monitor import Monitor

@click.command()
@click.option('--pre', default=30, help='Pre-run duration in seconds')
@click.option('--post', default=30, help='Post-run duration in seconds')
@click.option('--output', type=click.Path(), help='Output directory for logs')
@click.option('--clean', is_flag=True, help='Clean previous log directories')
def main(pre: int, post: int, output: str, clean: bool):
    if clean:
        for path in Path.cwd().glob('logs_*'):
            if path.is_dir():
                for file in path.rglob('*'):
                    file.unlink()
                path.rmdir()
        return

    monitor = Monitor()
    monitor.run(pre_duration=pre, post_duration=post, output_dir=output)

if __name__ == '__main__':
    main()
