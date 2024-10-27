# __init__.py
"""WebImport module.

This module contains the "webimport" import handler.

Attributes:
    logger (logging.logger): The logger for the WebImporter.

Functions:
    register(location=None, port=None, override=False): Registers a webimport handler.

Usage:
    ```python
    # Depending on the method of loading webimport, either:
    register('my.server', 8080)
    # or
    webimport.register('my.server', 8080)
    # Then:
    import my_module
    ```
"""

from webimport.webimport import register
from webimport.webimport import logger
