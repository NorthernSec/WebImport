_MOD_IS_PRESENT_  = 1
_MOD_NOT_PRESENT_ = 0
_MOD_SEARCHING_   = -1
_MOD_UNKNOWN_     = -2

import encodings.idna
import http.client
import importlib
import importlib.abc
import logging
import sys

_LOG_LEVEL_ = logging.WARNING

logging.basicConfig(level=_LOG_LEVEL_, format='%(levelname)-7s:%(message)s')

logging.getLogger("WIMP")

def register(port, location='localhost', override=False, caching=False):
    WebImporter.port     = port
    WebImporter.location = location
    WebImporter.override = override
    WebImporter.caching  = caching
    logging.info("Registered to %s:%s, override: %s"%(location, port, override))
    if override:
        flush_modules()


def flush_modules():
    mods = list(set([x.__name__ for x in sys.modules.values()]))
    for key in mods:
        if (not key.startswith('_') and not 'importlib' in key and
            key not in ['sys', 'builtins', 'encodings.idna',
                        'http.client', 'logging']):
            del sys.modules[key]
            logging.debug("[%s] Flushed"%key)
    logging.info("Flushed all non-system modules")


class WebImporter(importlib.abc.SourceLoader, importlib.abc.MetaPathFinder):
    port     = None
    location = 'localhost'
    modules  = {} # structure: [present local, present remote]
    logging.info("Initialized")


    def _is_present_locally(self, fullname):
        status = self.modules.get(fullname, [_MOD_UNKNOWN_, _MOD_UNKNOWN_])
        if status[0] == _MOD_UNKNOWN_:
            logging.debug("[%s]  |- Not chached. Searching..."%fullname)
            status[0] = _MOD_SEARCHING_
            self.modules[fullname] = status
            loader = importlib.find_loader(fullname)
            status[0] = _MOD_IS_PRESENT_ if loader else _MOD_NOT_PRESENT_
            self.modules[fullname] = status
        if bool(status[0]):
            logging.info("[%s]  |    |- Found locally"%fullname)
        else:
            logging.info("[%s]  |    |- Not found locally"%fullname)
        return bool(status[0])


    def _is_present_remote(self, fullname):
        status = self.modules.get(fullname, [_MOD_UNKNOWN_, _MOD_UNKNOWN_])
        if self.caching and (status[1] != _MOD_UNKNOWN_):
            if bool(status[1]):
                logging.debug("[%s] Cache | available remote"%fullname)
            else:
                logging.debug("[%s] Cache | Not available remote"%fullname)
            return bool(status[1])
        try:
            logging.info("[%s]  |- Checking remote availability"%fullname)
            r = self._do_search(fullname)
        except ValueError as e:
            print(e)
            status[1] = _MOD_NOT_PRESENT_
        else:
            if r != None:
                 logging.debug("[%s]  |   |- Available at %s"%(fullname, r))
                 status[1] = r
            else:
                logging.debug("[%s]  |   |- Not available remote"%fullname)
                status[1] = _MOD_NOT_PRESENT_
            self.modules[fullname] = status
        return bool(status[1])


    def is_package(self, fullname):
        path = self.modules.get(fullname, ['', ''])[1]
        return path.endswith('/__init__.py')


    def get_filename(self, fullname):
        return fullname


    def find_module(self, fullname, *args, **kwargs):
        logging.info("[%s] Finding module"%fullname)
        status = self.modules.get(fullname, [_MOD_UNKNOWN_, _MOD_UNKNOWN_])
        # If find_module is triggered while searching locally, ignore
        if status[0] == _MOD_SEARCHING_:
            return None
        # Unless overridden: First try to import locally
        if not self.override and self._is_present_locally(fullname):
            logging.debug("[%s]  |- Loading locally instead"%fullname)
            return None
        # Check if package is available remotely
        if self._is_present_remote(fullname):
            logging.debug("[%s]  |- WAMP can load this"%fullname)
            return self
        return None


    def find_spec(self, fullname, *args, **kwargs):
        if not self.find_module(fullname):
            return None
        logging.info("[%s]  |- Loading spec"%fullname)
        if self.is_package(fullname):
            logging.debug("[%s]  |   |- Spec is a package"%fullname)
        spec = importlib.machinery.ModuleSpec(fullname, self, is_package=self.is_package(fullname))
        return spec


    def get_data(self, fullname):
        logging.info("[%s]  |- Fetching source"%fullname)
        try:
            assert isinstance(self.port, int)
            # We assume that by this point, we have located the module
            path = self.modules[fullname][1]
            url = self.get_filename(fullname)
            r = self._do_request(path)
            if r.status == 200:
                logging.debug("[%s]  |   |- Source found"%fullname)
                code = r.read()
            elif self.is_package(fullname):
                # init missing. add empty one
                logging.debug("[%s]  |   |- Source missing. Using empty __init__.py"%fullname)
                code = ''
            else:
                logging.error("[%s]  |   |- Not available remote!"%fullname)
                raise Exception("Module not available remotely")
            # Build module
            return code
        except Exception as e:
            logging.error("[%s] Exception happened: %s"%(fullname, e))
        return None


    def _do_search(self, fullname):
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
        c = http.client.HTTPConnection(self.location, self.port)
        c.request("GET", fullname)
        return c.getresponse()


sys.meta_path.insert(0,WebImporter())

if __name__ == '__main__':
    register(8000)

