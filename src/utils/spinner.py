"""Simple ASCII spinner animation utility."""

import sys
import time
import threading
from contextlib import contextmanager


class Spinner:
    """Simple ASCII spinner animation."""
    
    def __init__(self, message="Working"):
        self.message = message
        self.frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the spinner animation."""
        self.running = True
        self.thread = threading.Thread(target=self._animate)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        """Stop the spinner and clear the line."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.1)
        # Clear the line
        sys.stdout.write('\r' + ' ' * (len(self.message) + 10) + '\r')
        sys.stdout.flush()
    
    def _animate(self):
        """Internal animation loop."""
        frame_index = 0
        while self.running:
            frame = self.frames[frame_index % len(self.frames)]
            sys.stdout.write(f'\r{frame} {self.message}...')
            sys.stdout.flush()
            time.sleep(0.1)
            frame_index += 1


@contextmanager
def spinner(message="Working"):
    """Context manager for spinner usage."""
    s = Spinner(message)
    try:
        s.start()
        yield s
    finally:
        s.stop() 