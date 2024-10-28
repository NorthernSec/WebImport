#!/usr/bin/env python3
"""WebImport.

This library provides a remote import handler called "webimport".

Classes:
    WebImporter:

Methods:
    register():      Register the webimport import handler with specified settigns.
    flush_modules(): Flush out currently loaded modules.
"""
# Flags
_MOD_IS_PRESENT_  = 1
_MOD_NOT_PRESENT_ = 0
_MOD_SEARCHING_   = -1
_MOD_UNKNOWN_     = -2

# Imports
import encodings.idna
import http.client
import importlib
import importlib.abc
import importlib.util
import logging
import sys

# Logger
_LOG_LEVEL_ = logging.WARNING
logging.basicConfig(level=_LOG_LEVEL_, format='%(levelname)-7s:%(message)s')
logger = logging.getLogger("WIMP")


def register(location=None, port=None, override=False):
    """Register the WebImport import handler with certain settings.

    Args:
        location (str):  The url of the webserver.
        port     (int):  The port of the webserver.
        override (bool): Set to True if you want to prioritize external libraries
                          over local ones.
    Notes:
        Please note that you can register multiple webimport loaders. Keep that in
          mind in case you run into bugs. You can check your `sys.meta_path` for
          the available import handlers, and remove them from there if necessary.
    """
    WebImporter.location = location or 'localhost'
    WebImporter.port     = port     or 8080
    WebImporter.override = override
    if not isinstance(WebImporter.location, str):
        raise ValueError("location' should be a string")
    if not isinstance(WebImporter.port, int):
        raise ValueError("'port' should be an integer")
    logger.info("Registered to %s:%s, override: %s"%(location, port, override))
    if override:
        flush_modules()
    sys.meta_path.insert(0,WebImporter())


def flush_modules():
    """'un-imports' all non-system libraries that are not used by webimport."""
    mods = list({x.__name__ for x in sys.modules.values()})
    for key in mods:
        if (not key.startswith('_') and not 'importlib' in key and
            key not in ['sys', 'builtins', 'encodings.idna',
                        'http.client', 'logging']):
            del sys.modules[key]
            logger.debug("[%s] Flushed"%key)
    logger.info("Flushed all non-system modules")


class WebImporter(importlib.abc.SourceLoader, importlib.abc.MetaPathFinder):
    """The "WebImporter" import handler class.

    Methods:

    """
    port     = None
    location = 'localhost'
    override = False
    modules  = {}  # structure: [present local, present remote]
    logger.info("Initialized")


    def _is_present_locally(self, fullname):
        """Checks if a library is present locally."""
        status = self.modules.get(fullname, [_MOD_UNKNOWN_, _MOD_UNKNOWN_])
        if status[0] == _MOD_UNKNOWN_:
            logger.debug("[%s]  |- Not chached. Searching..."%fullname)
            status[0] = _MOD_SEARCHING_
            self.modules[fullname] = status
            loader = importlib.util.find_spec(fullname)
            status[0] = _MOD_IS_PRESENT_ if loader else _MOD_NOT_PRESENT_
            self.modules[fullname] = status
        if bool(status[0]):
            logger.info("[%s]  |    |- Found locally"%fullname)
        else:
            logger.info("[%s]  |    |- Not found locally"%fullname)
        return bool(status[0])


    def _is_present_remote(self, fullname):
        """Checks if a library is present remotely."""
        status = self.modules.get(fullname, [_MOD_UNKNOWN_, _MOD_UNKNOWN_])
        try:
            logger.info("[%s]  |- Checking remote availability"%fullname)
            r = self._do_search(fullname)
        except ValueError as e:
            print(e)
            status[1] = _MOD_NOT_PRESENT_
        else:
            if r != None:
                 logger.debug("[%s]  |   |- Available at %s"%(fullname, r))
                 status[1] = r
            else:
                logger.debug("[%s]  |   |- Not available remote"%fullname)
                status[1] = _MOD_NOT_PRESENT_
            self.modules[fullname] = status
        return bool(status[1])


    def is_package(self, fullname):
        """Checks if the provided name is that of a package (is an __init__.py).

        Args:
            fullname (str): the full name of a package.

        Returns:
            bool: True if the module is a package.
        """
        path = self.modules.get(fullname, ['', ''])[1]
        return path.endswith('/__init__.py')


    def get_filename(self, fullname):
        """Gets the filename."""
        return fullname


    def find_module(self, fullname, *args, **kwargs):
        """Checks if WebImport can and should load this module.

        Args:
            fullname (str): The full path of the module.

        Returns:
            None | WebImporter: Returns itself if WebImport should load the module,
                                  otherwise returns None
        """
        logger.info("[%s] Finding module"%fullname)
        status = self.modules.get(fullname, [_MOD_UNKNOWN_, _MOD_UNKNOWN_])
        # If find_module is triggered while searching locally, ignore
        if status[0] == _MOD_SEARCHING_:
            return None
        # Unless overridden: First try to import locally
        if not self.override and self._is_present_locally(fullname):
            logger.debug("[%s]  |- Loading locally instead"%fullname)
            return None
        # Check if package is available remotely
        if self._is_present_remote(fullname):
            logger.debug("[%s]  |- WAMP can load this"%fullname)
            return self
        return None


    def find_spec(self, fullname, path, target=None):
        """Gets the spec of the library"""
        if not self.find_module(fullname,path):
            return None
        logger.info("[%s]  |- Loading spec"%fullname)
        if self.is_package(fullname):
            logger.debug("[%s]  |   |- Spec is a package"%fullname)
        origin = self.modules.get(fullname)[1]
        spec = importlib.util.spec_from_loader(fullname, self, origin=origin,
                                               is_package=self.is_package(fullname))
        return spec


    def get_data(self, fullname):
        """Gets the module code from the remote server.

        Args:
            fullname (str): The full path of the module you want to load.

        Returns:
            str: The code of the module.
        """
        logger.info("[%s]  |- Fetching source"%fullname)
        try:
            assert isinstance(self.port, int)
            # We assume that by this point, we have located the module
            path = self.modules[fullname][1]
            url = self.get_filename(fullname)
            r = self._do_request(path)
            if r.status == 200:
                logger.debug("[%s]  |   |- Source found"%fullname)
                code = r.read()
            elif self.is_package(fullname):
                # init missing. add empty one
                logger.debug("[%s]  |   |- Source missing. Using empty __init__.py"%fullname)
                code = ''
            else:
                logger.error("[%s]  |   |- Not available remote!"%fullname)
                raise Exception("Module not available remotely")
            # Build module
            return code
        except Exception as e:
            logger.error("[%s] Exception happened: %s"%(fullname, e))
        return None


    def _do_search(self, fullname):
        """Check if the module is available remotely, and return the file name.

        Args:
            fullname (str): The full name of the module.

        Returns:
            str | None: The path of the module on the remote server or None
        """
        # We're dealing with dirs here
        fullname = '/'.join(fullname.split('.'))
        for extension in ["", '.py']:
            test = fullname+extension
            c = http.client.HTTPConnection(self.location, self.port)
            c.request("HEAD", test)
            r = c.getresponse()
            if r.status == 200:
                 return test
            elif r.status == 301:
                return test+'/__init__.py'
        return None


    def _do_request(self, fullname):
        """Make a request to the remote server.

        Args:
            fullname (str): The full name of the requested module.

        Returns:
            http.client.HTTPResponse: The response of the webserver
        """
        c = http.client.HTTPConnection(self.location, self.port)
        c.request("GET", fullname)
        return c.getresponse()
