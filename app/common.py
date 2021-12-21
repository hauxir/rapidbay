import os
import threading


def threaded(fn):
    """
    A decorator that runs the decorated function in a separate thread.
    """
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread

    return wrapper


def path_hierarchy(path):
    """
    This function returns a dictionary that represents the hierarchy of the
    directory structure
    """
    hierarchy = os.path.basename(path)
    try:
        return {
            hierarchy: [
                path_hierarchy(os.path.join(path, contents))
                for contents in os.listdir(path)
            ]
        }
    except OSError as e:
        pass
    if hierarchy == "":
        return []
    return hierarchy
