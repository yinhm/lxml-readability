import os.path
import re
import subprocess
import sys
import urllib2
import urlparse

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
                '--convert-links',
                '--backup-converted',
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

        rel_path = wget_saved_to(output)
        if rel_path is None:
            raise Exception('could not figure out where wget saved to')
        self._url_map[url] = rel_path
        # TODO: Log.
        print('%s: %s' % (url, rel_path))
        path = os.path.join(self._base_path, rel_path)
        with open(path, 'r') as f:
            return f.read()

def wget_saved_to(wget_output):
    save_re = re.compile(r'Saving to: \xe2\x80\x9c(.*)\xe2\x80\x9d')
    lines = wget_output.splitlines()
    for line in lines:
        m = save_re.match(line)
        if m:
            return m.group(1)
    return None

def adjust_extension(path):
    if not HTML_RE.search(path):
        return path + '.html'
    else:
        return path

def main():
    if len(sys.argv) == 3:
        print 'fetching local copy'
        fetcher = LocalCopyUrlFetch(TEST_DATA_PATH, sys.argv[1])
        contents = fetcher.urlread(sys.argv[2])
    else:
        pass

if __name__ == '__main__':
    main()
