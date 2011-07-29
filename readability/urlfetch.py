import logging
import os.path
import re
import subprocess
import sys
import urllib2
import urlparse
import wget_parser

HTML_RE = re.compile(r'\.[Hh][Tt][Mm][Ll]?$')

class UrlFetch():
    """
    A class for fetching URLs.  This provides a layer of abstraction that can
    be easily replaced for testing.
    """

    def urlread(self, url):
        return urllib2.urlopen(url).read()

class MockUrlFetch(UrlFetch):

    def __init__(self, base_path, url_map):
        self._base_path = base_path
        self._url_map = url_map

    def urlread(self, url):
        path = os.path.join(self._base_path, self._url_map[url])
        with open(path, 'r') as f:
            return f.read()

class LocalCopyUrlFetch(UrlFetch):

    def __init__(self, base_path, url_map):
        self._base_path = base_path
        self._url_map = url_map

    def urlread(self, url):
        if subprocess.call('which wget', shell = True) != 0:
            raise Exception('wget required but not found on PATH')

        argv = [
                'wget',
                '--adjust-extension',
                '--span-hosts',
                '--page-requisites',
                url
                ]
        try:
            output = subprocess.check_output(
                    argv,
                    cwd = self._base_path,
                    stderr = subprocess.STDOUT
                    )
        except subprocess.CalledProcessError as e:
            # TODO: Log this instead of just printing it.
            output = e.output
            print('wget exited with non-zero code: %d' % e.returncode)

        parser = wget_parser.WgetParser(self._url_map)
        parser.parse(output)

        if url not in self._url_map:
            raise Exception('%s was not successfully fetched' % url)
        
        path = os.path.join(self._base_path, self._url_map[url])
        with open(path, 'r') as f:
            return f.read()

def adjust_extension(path):
    if not HTML_RE.search(path):
        return path + '.html'
    else:
        return path

def main():
    logging.basicConfig(level = logging.DEBUG)
    if len(sys.argv) == 3:
        print 'fetching local copy'
        url_map = dict()
        fetcher = LocalCopyUrlFetch(sys.argv[2], url_map)
        contents = fetcher.urlread(sys.argv[1])
    else:
        pass

if __name__ == '__main__':
    main()
