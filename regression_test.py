"""
This module provides a regression test for results of running the readability
algorithm on a variety of different real-world examples.  For each page in the
test suite, a benchmark was captured that represents the current readability
results.  Note that these are not necessarily ideal results, just the ones used
as a benchmark.

This allows you to tweak and change the readability algorithm and see how it
changes existing results, hopefully for the better.


Running the test
----------------

To run the regression suite:

    $ python regression_test.py

This will generate a regression_test_output/ directory.  Open
regression_test_output/index.html in a web browser to examine the results.

For each test, you can examine the original version, the benchmark readability
version, the current readability version (using your working code), and a diff
version between the benchmark and current versions.

You can run a subset of tests by using the '--case' option:

    $ python regression_test.py --case arstechnica-000 --case slate-000

This invocation will only run the arstechnica-000 and slate-000 test cases.
This is handy for speeding up your testing cycle if you are working on specific
improvements.


Generating a new test case
--------------------------

Each test case is defined by a specification YAML file (test_name.yaml) and a
directory holding resources used by the test (test_name/).  These both live in
the regression_test_data/ directory.

By far, the easiest way to create a new regression test case is by using the
gen_test.py program.

For example:
    
    $ python gen_test.py create "http://foo.com/bar" foo-000 "foo article"

This will generate a new test case named 'foo-000' for the given URL with the
description "foo article".  The benchmark for the test will be generated with
the current readability algorithm.

This program does what it can to bring any resources used by the page local.
For example, images used by the original page are downloaded so that the test
can run entirely locally, and results can be viewed complete with images.
"""
from lxml.html import builder as B
from regression_test_css import SUMMARY_CSS, READABILITY_CSS
import argparse
import logging
import lxml.html
import lxml.html.diff
import os
import os.path
import re
import readability
import shutil
import sys
import urllib
import urlparse
import readability.urlfetch as urlfetch
import yaml

YAML_EXTENSION = '.yaml'
READABLE_SUFFIX = '.rdbl'
RESULT_SUFFIX = '.result'
DIFF_SUFFIX = '.diff'

TEST_DATA_PATH = 'regression_test_data'
TEST_OUTPUT_PATH = 'regression_test_output'
TEST_SUMMARY_PATH = os.path.join(TEST_OUTPUT_PATH, 'index.html')

class ReadabilityTest:

    def __init__(
            self,
            dir_path,
            enabled,
            name,
            url,
            desc,
            notes,
            url_map
            ):
        self.dir_path = dir_path
        self.enabled = enabled
        self.name = name
        self.url = url
        self.desc = desc
        self.notes = notes
        self.url_map = url_map

class ReadabilityTestData:

    def __init__(self, test, orig_html, rdbl_html):
        self.test = test
        self.orig_html = orig_html
        self.rdbl_html = rdbl_html

class ReadabilityTestResult:

    def __init__(self, test_data, result_html, diff_html):
        self.test_data = test_data
        self.result_html = result_html
        self.diff_html = diff_html

def read_yaml(path):
    with open(path, 'r') as f:
        return yaml.load(f)

def make_readability_test(dir_path, name, spec_dict):
    enabled = spec_dict.get('enabled', True)
    notes = spec_dict.get('notes', '')
    url_map = spec_dict.get('url_map', dict())
    return ReadabilityTest(
            dir_path,
            enabled,
            name,
            spec_dict['url'],
            spec_dict['test_description'],
            notes,
            url_map
            )

def load_test_data(test):
    def read_data(suffix):
        rel_path = test.url_map[test.url] + suffix
        path = os.path.join(TEST_DATA_PATH, test.name, rel_path)
        return open(path, 'r').read()

    if test.enabled:
        orig = read_data('')
        rdbl = read_data(READABLE_SUFFIX)
        return ReadabilityTestData(test, orig, rdbl)
    else:
        return None

def load_readability_tests(dir_path, files, cases):
    yaml_files = [f for f in files if f.endswith(YAML_EXTENSION)]
    yaml_paths = [os.path.join(dir_path, f) for f in yaml_files]
    names = [re.sub('.yaml$', '', f) for f in yaml_files]
    spec_dicts = [read_yaml(p) for p in yaml_paths]
    return [
            make_readability_test(dir_path, name, spec_dict)
            for (name, spec_dict) in zip(names, spec_dicts)
            if cases is None or name in cases
            ]

def execute_test(test_data):
    if test_data is None:
        return None
    else:
        base_path = os.path.join(TEST_DATA_PATH, test_data.test.name)
        fetcher = urlfetch.MockUrlFetch(base_path, test_data.test.url_map)
        doc = readability.Document(
                test_data.orig_html,
                url = test_data.test.url,
                urlfetch = fetcher
                )
        summary = doc.summary()
        diff = lxml.html.diff.htmldiff(test_data.rdbl_html, summary.html)
        return ReadabilityTestResult(test_data, summary.html, diff)

def element_string_lengths(elems):
    return [len(e.xpath('string()')) for e in elems]

class ResultSummary():

    def __init__(self, result):
        # logging.debug('diff: %s' % result.diff_html)
        doc = lxml.html.document_fromstring(
                '<html><body>' + result.diff_html + '</body></html>')

        insertions = doc.xpath('//ins')
        insertion_lengths = element_string_lengths(insertions)
        self.insertions = sum(insertion_lengths)
        self.insertion_blocks = len(insertions)

        deletions = doc.xpath('//del')
        deletion_lengths = element_string_lengths(deletions)
        self.deletions = sum(deletion_lengths)
        self.deletion_blocks = len(deletions)

        # doc = lxml.html.fragment_fromstring('<div></div>')
        # self.insertions = 0
        # self.insertion_blocks = 0
        # self.deletions = 0
        # self.deletion_blocks = 0

def make_summary_row(test, result):
    def output(suffix):
        rel_path = test.url_map[test.url]
        return urllib.quote(os.path.join(test.name, rel_path) + suffix)

    if test.enabled:
        s = ResultSummary(result)
        return B.TR(
                B.TD(test.name),
                B.TD('%d (%d)' % (s.insertions, s.insertion_blocks)),
                B.TD('%d (%d)' % (s.deletions, s.deletion_blocks)),
                B.TD(
                    B.A('original', href = output('')),
                    ' ',
                    B.A('benchmark', href = output(READABLE_SUFFIX)),
                    ' ',
                    B.A('result', href = output(RESULT_SUFFIX)),
                    ' ',
                    B.A('diff', href = output(DIFF_SUFFIX))
                    ),
                B.TD(test.notes)
                )
    else:
        return B.TR(
                B.CLASS('skipped'),
                B.TD('%s (SKIPPED)' % test.name),
                B.TD('N/A'),
                B.TD('N/A'),
                B.TD('N/A'),
                B.TD(test.notes)
                )

def make_summary_doc(tests_w_results):
    tbody = B.TBODY(
            B.TR(
                B.TH('Test Name'),
                B.TH('Inserted (in # of blocks)'),
                B.TH('Deleted (in # of blocks)'),
                B.TH('Links'),
                B.TH('Notes')
                )
            )
    for (test, result) in tests_w_results:
        row = make_summary_row(test, result)
        tbody.append(row)
    return B.HTML(
            B.HEAD(
                B.TITLE('Readability Test Summary'),
                B.STYLE(SUMMARY_CSS, type = 'text/css')
                ),
            B.BODY(
                B.TABLE(
                    tbody
                    )
                )
            )

def write_summary(path, tests_w_results):
    doc = make_summary_doc(tests_w_results)
    with open(path, 'w') as f:
        f.write(lxml.html.tostring(doc))

def add_css(doc):
    style = B.STYLE(READABILITY_CSS, type = 'text/css')
    head = B.HEAD(style, content = 'text/html; charset=utf-8')
    doc.insert(0, head)

def convert_links(url_map, url, doc):
    url_path = url_map[url]
    url_dir = os.path.dirname(url_path)
    logging.debug('converting links: url_dir: %s' % url_dir)
    def link_repl_func(link):
        if link in url_map:
            link_path = url_map[link]
            logging.debug('converting links: link_path: %s' % link_path)
            new_link = os.path.relpath(link_path, url_dir)
            logging.debug('converting links: new_link: %s' % new_link)
            return urllib.quote(new_link)
        else:
            split_link = urlparse.urlsplit(link)
            if split_link.scheme == '':
                if split_link.path == '':
                    return link
                elif split_link.path[0] == '/':
                    root_path = urlparse.urlsplit(url).netloc
                    link_path = os.path.join(root_path, split_link.path[1:])
                    new_link = os.path.relpath(link_path, url_dir)
                    return urllib.quote(new_link)
                else:
                    new_link = os.path.join(url_dir, split_link.path)
                    return urllib.quote(new_link)
            else:
                return link
    doc.rewrite_links(link_repl_func)

def write_output_html(url_map, url, html, path, should_add_css):
    doc = lxml.html.document_fromstring(html)
    if should_add_css:
        add_css(doc)
    convert_links(url_map, url, doc)
    html = lxml.html.tostring(doc)
    with open(path, 'w') as f:
        f.write(html)

def write_result(output_dir_path, result):
    test_name = result.test_data.test.name

    # Copy the base_path to output_base_path so that the result has access to
    # any images it needs to display properly.  This will also copy the
    # original page and benchmark readability result.
    base_path = os.path.join(TEST_DATA_PATH, test_name)
    output_base_path = os.path.join(TEST_OUTPUT_PATH, test_name)
    shutil.rmtree(output_base_path, ignore_errors = True)
    shutil.copytree(base_path, output_base_path)

    # Write pretty versions of the benchmark, result, and diffs into the
    # output.  Note that this will overwrite the original and benchmark that we
    # copied over.
    specs = [
            (result.test_data.orig_html, '', False),
            (result.test_data.rdbl_html, READABLE_SUFFIX, True),
            (result.result_html, RESULT_SUFFIX, True),
            (result.diff_html, DIFF_SUFFIX, True)
            ]
    for (html, suffix, add_css) in specs:
        url = result.test_data.test.url
        url_map = result.test_data.test.url_map
        url_path = url_map[url]
        path = os.path.join(output_dir_path, test_name, url_path) + suffix
        write_output_html(url_map, url, html, path, add_css)

def print_test_info(test):
    name_string = '%s' % test.name
    if test.enabled:
        skipped = ''
    else:
        skipped = ' (SKIPPED)'
    print('%20s: %s%s' % (name_string, test.desc, skipped))

def run_readability_tests(cases):
    files = os.listdir(TEST_DATA_PATH)
    tests = load_readability_tests(TEST_DATA_PATH, files, cases)
    test_datas = [load_test_data(t) for t in tests]
    results = [execute_test(t) for t in test_datas]
    for (test, result) in zip(tests, results):
        print_test_info(test)
        if result:
            write_result(TEST_OUTPUT_PATH, result)
    write_summary(TEST_SUMMARY_PATH, zip(tests, results))

DESCRIPTION = 'Run the readability regression test suite.'

def main():
    parser = argparse.ArgumentParser(description = DESCRIPTION)

    parser.add_argument(
            '--debug',
            action = 'store_const',
            const = True,
            default = False,
            help = 'enable debug logging'
            )
    parser.add_argument(
            '--case',
            action = 'append',
            help = 'a test case to run'
            )

    args = parser.parse_args()
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level = level)
    run_readability_tests(args.case)

if __name__ == '__main__':
    main()
