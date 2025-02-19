import functools
import traceback

def component_check(component_name):
    """
    A decorator that catches any exception thrown by a component,
    prints a message identifying which component failed, and then re-raises the error.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"[ERROR] Component '{component_name}' failed: {e}")
                traceback.print_exc()
                raise
        return wrapper
    return decorator 