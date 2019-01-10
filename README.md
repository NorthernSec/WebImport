# WebImport
Import python libraries over HTTP

## Goal
Allow you to load python modules from a system, when they are not present 
 on the system. <br />
**Note:** written for **python 3** <br />
**Note:** The code has been tested on **Ubuntu 16.04 LTS**

## Use cases
 * Running dynamic code from a read-only filesystem
 * Using non-standard packages on a machine without leaving traces
 * Testing code on devices you cannot install packages on

## How to use
If WebImporter is available on a given system, you can import it as shown
 below:

    import webimport
    webimport.register(8000, location='some.http.server', override=False)

The register command takes 3 arguments.
 * port (Required): The port to connect to
 * location (optional): The host to connect to. Default: localhost
 * override: (optional): Try to import from remote first. Default: False

### Example uses:
#### Running scripts with shared modules over ssh:

First Terminal

    cd /path/to/python/libs
    python3 -m "http.server" 8000

Second Terminal

    cat webimport/webimport.py script.py | ssh -R 8000:localhost:8000 user@some.server 'cat -|python3'

