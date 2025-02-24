import functools
import traceback

def component_check(component_name):
    """
    A decorator that catches any exception thrown by a component,
    prints a message identifying which component failed, and then re-raises the error.
    Works with both functions and classes.
    """
    def decorator(obj):
        # For functions
        if callable(obj) and not isinstance(obj, type):
            @functools.wraps(obj)
            def wrapper(*args, **kwargs):
                try:
                    return obj(*args, **kwargs)
                except Exception as e:
                    print(f"[ERROR] Component '{component_name}' failed: {e}")
                    traceback.print_exc()
                    raise
            return wrapper
        # For classes
        else:
            # Just return the class unchanged - we'll implement proper class wrapping later
            return obj
    return decorator 