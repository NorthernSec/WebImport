# WebImport
Import python libraries over HTTP.
This package allows you to load python modules on a system where these packages may not be available.
It uses a HTTP connection to fetch these packages remotely.

This package is written for Python3.4 or newer.

## Use cases
 * Running dynamic code from a read-only filesystem
 * Using non-standard packages on a machine without leaving traces
 * Testing code on devices you cannot install packages on

## How to use
If WebImporter is available on a given system, you can import it as shown below:
```python
    import webimport
    webimport.register(location='some.http.server', port=8080, override=False)
```
The register command takes 3 arguments.
 * location (optional): The host to connect to. Default: localhost
 * port (optional): The port to connect to. Default: 8080
 * override: (optional): Try to import from remote first. Default: False

### Preparing the server
To create the webserver to serve the libraries, you should create a single directory containing all these packages.

To do this, an easy method to do this would be:
```sh
mkdir my_package_dir
pip install <package> --target my_package_dir
```

### Example uses:
#### Running scripts with shared modules over ssh:

First Terminal
```sh
cd /path/to/python/libs
python3 -m "http.server" 8000
```
Second Terminal
```sh
cat webimport/webimport.py script.py | ssh -R 8000:localhost:8000 user@some.server 'cat -|python3'
```

#### Running scripts without SSH tunnel:
Set up the webserver with the webimport-server command (requires pip installation of webimport):
```sh
webimport-server my_package_dir
```

From the other device, you can run any of the following:

**Open a terminal and pre-load the webimport code**
```sh
python3 -i -c "$(curl server-url:8080/_hook)"
```
