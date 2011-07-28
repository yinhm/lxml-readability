"""
This program facilitates the creation of a regression test case as used by the
test module.  It uses the current readability algorithm to capture a benchmark
and construct a new test case.
"""
from regression_test import (
        TEST_DATA_PATH,
        READABLE_SUFFIX,
        YAML_EXTENSION,
        read_yaml
        )
import argparse
import errno
import os
import os.path
import readability
import readability.urlfetch as urlfetch
import sys
import urllib2
import urlparse
import yaml

OVERWRITE_QUESTION = '%s exists; overwrite and continue (y/n)? '

def y_or_n(question):
    while True:
        response = raw_input(question).strip()
        if len(response) > 0:
            return response[0] in ['y', 'Y']

def write_file(path, data):
    mode = 0644
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    except OSError as e:
        if e.errno == errno.EEXIST:
            if y_or_n(OVERWRITE_QUESTION % path):
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
            else:
                return False
        else:
            raise e
    f = os.fdopen(fd, 'w')
    f.write(data)
    return True

def make_readable_path(base_path, url_map, url):
    # We put the readable version of the page next to the original so that all
    # of the relative links work when we open it in a browser.
    rel_path = url_map[url]
    path = os.path.join(base_path, rel_path)
    return ''.join([path, READABLE_SUFFIX])

def write_readable(base_path, fetcher, url_map, url):
    orig = fetcher.urlread(url)

    options = {'url': url, 'urlfetch': fetcher}
    rdbl_doc = readability.Document(orig, **options)
    summary = rdbl_doc.summary()

    path = make_readable_path(base_path, url_map, url)
    return write_file(path, summary.html)

def read_spec(test_name):
    yaml_path = os.path.join(TEST_DATA_PATH, test_name + YAML_EXTENSION)
    return read_yaml(yaml_path)

def write_spec(base_path, spec):
    spec_yaml = yaml.dump(spec, default_flow_style = False)
    path = base_path + YAML_EXTENSION
    return write_file(path, spec_yaml)

def maybe_mkdir(path):
    try:
        os.mkdir(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise e

def create(args):
    spec = {'url': args.url, 'test_description': args.test_description}

    # We retrieve the page and all of its prerequisites so that it can be
    # displayed fully locally.  base_path is the path to the directory that
    # holds the structure of the site(s) necessary for the prerequisites.
    base_path = os.path.join(TEST_DATA_PATH, args.test_name)
    maybe_mkdir(base_path)

    url_map = dict()
    fetcher = readability.urlfetch.LocalCopyUrlFetch(base_path, url_map)

    if not write_readable(base_path, fetcher, url_map, args.url):
        return False

    spec['url_map'] = url_map
    if not write_spec(base_path, spec):
        return False

    return True

def genbench(args):
    spec = read_spec(args.test_name)
    url = spec['url']

    base_path = os.path.join(TEST_DATA_PATH, args.test_name)

    if args.refetch:
        url_map = dict()
        fetcher = readability.urlfetch.LocalCopyUrlFetch(base_path, url_map)
    else:
        url_map = spec['url_map']
        fetcher = readability.urlfetch.MockUrlFetch(base_path, url_map)

    if not write_readable(base_path, fetcher, url_map, url):
        return False

    if args.refetch:
        # We potentially refetched different pages than the existing test, so
        # we have to update the spec accordingly.
        spec['url_map'] = url_map
        if not write_spec(base_path, spec):
            return False

    return True

DESCRIPTION = 'Create a readability regression test case.'

def main():
    parser = argparse.ArgumentParser(description = DESCRIPTION)
    subparsers = parser.add_subparsers(help = 'available subcommands')

    parser_create = subparsers.add_parser(
            'create',
            help = 'create an entirely new test'
            )
    parser_create.add_argument(
            'url',
            metavar = 'url',
            help = 'the url for which to generate a test'
            )
    parser_create.add_argument(
            'test_name',
            metavar = 'test-name',
            help = 'the name of the test'
            )
    parser_create.add_argument(
            'test_description',
            metavar = 'test-description',
            help = 'the description of the test'
            )
    parser_create.set_defaults(func = create)

    parser_genbench = subparsers.add_parser(
            'genbench',
            help = 'regenerate the benchmark for an existing test'
            )
    parser_genbench.add_argument(
            'test_name',
            metavar = 'test-name',
            help = 'the name of the test'
            )
    parser_genbench.add_argument(
            '--refetch',
            dest = 'refetch',
            action = 'store_const',
            const = True,
            default = False,
            help = 'if set, original html is refetched from the url'
            )
    parser_genbench.set_defaults(func = genbench)

    args = parser.parse_args()
    result = args.func(args)
    if not result:
        print('test was not fully generated')

if __name__ == '__main__':
    main()
