from readability import *
import unittest

class TestFindBaseUrl(unittest.TestCase):

    def setUp(self):
        self.longMessage = True

    def _assert_url(self, url, expected_base_url, msg = None):
        actual_base_url = find_base_url(url)
        self.assertEqual(expected_base_url, actual_base_url, msg)

    def _run_urls(self, specs):
        """
        Asserts expected results on a sequence of specs, where each spec is a
        pair: (URL, expected base URL).
        """
        for spec in specs:
            url = spec[0]
            expected = spec[1]
            if len(spec) > 2:
                msg = spec[2]
            else:
                msg = None
            self._assert_url(url, expected, msg)

    def test_none(self):
        self._assert_url(None, None)

    def test_no_change(self):
        url = 'http://foo.com/article'
        self._assert_url(url, url)

    def test_extension_stripping(self):
        specs = [
                (
                'http://foo.com/article.html',
                'http://foo.com/article',
                'extension should be stripped'
                ),
                (
                'http://foo.com/path/to/article.html',
                'http://foo.com/path/to/article',
                'extension should be stripped'
                ),
                (
                'http://foo.com/article.123not',
                'http://foo.com/article.123not',
                '123not is not extension'
                ),
                (
                'http://foo.com/path/to/article.123not',
                'http://foo.com/path/to/article.123not',
                '123not is not extension'
                )
                ]
        self._run_urls(specs)

    def test_ewcms(self):
        self._assert_url(
                'http://www.ew.com/ew/article/0,,20313460_20369436,00.html',
                'http://www.ew.com/ew/article/0,,20313460_20369436'
                )

    def test_page_numbers(self):
        specs = [
                (
                'http://foo.com/page5.html',
                'http://foo.com',
                'page number should be stripped'
                ),
                (
                'http://foo.com/path/to/page5.html',
                'http://foo.com/path/to',
                'page number should be stripped'
                ),
                (
                'http://foo.com/article-5.html',
                'http://foo.com/article',
                'page number should be stripped'
                )
                ]
        self._run_urls(specs)

    def test_numbers(self):
        specs = [
                (
                'http://foo.com/5.html',
                'http://foo.com',
                'number should be stripped'
                ),
                (
                'http://foo.com/path/to/5.html',
                'http://foo.com/path/to',
                'number should be stripped'
                )
                ]
        self._run_urls(specs)

    def test_index(self):
        specs = [
                (
                'http://foo.com/index.html',
                'http://foo.com',
                'index should be stripped'
                ),
                (
                'http://foo.com/path/to/index.html',
                'http://foo.com/path/to',
                'index should be stripped'
                )
                ]
        self._run_urls(specs)

    def test_short(self):
        specs = [
                (
                'http://foo.com/en/1234567890',
                'http://foo.com/1234567890',
                'short segment should be stripped'
                ),
                (
                'http://foo.com/en/de/1234567890',
                'http://foo.com/en/1234567890',
                'short segment should be stripped'
                )
                ]
        self._run_urls(specs)

class TestFindNextPageLink(unittest.TestCase):

    def _test_page(self, url, html_path, expected):
        with open(html_path, 'r') as f:
            html = f.read()
        doc = parse(html, url)
        parsed_urls = {url}
        actual = find_next_page_url(parsed_urls, url, doc)
        self.assertEqual(expected, actual)

    def test_basic(self):
        self._test_page(
                'http://basic.com/article.html',
                'test_data/basic-multi-page.html',
                'http://basic.com/article.html?pagewanted=2'
                )

    def test_nytimes(self):
        # This better work for the New York Times.
        self._test_page(
                'http://www.nytimes.com/2011/07/10/magazine/the-dark-art-of-breaking-bad.html',
                'test_data/nytimes-next-page.html',
                'http://www.nytimes.com/2011/07/10/magazine/the-dark-art-of-breaking-bad.html?pagewanted=2&_r=1'
                )

class TestMultiPage(unittest.TestCase):
    '''
    Tests the full path of generating a readable page for a multi-page article.
    The test article is very simple, so this test should be resilient to tweaks
    of the algorithm.
    '''

    def _make_basic_url_map(self):
        url_fmt = 'http://basic.com/article.html?pagewanted=%s'
        file_fmt = 'basic-multi-page-%s.html'
        pairs = [(url_fmt % i, file_fmt % i) for i in ['2', '3']]
        return dict(pairs)

    def test_basic(self):
        with open('test_data/basic-multi-page.html', 'r') as f:
            html = f.read()
        url_map = self._make_basic_url_map()
        fetcher = urlfetch.MockUrlFetch('test_data', url_map)
        options = {
                'url': 'http://basic.com/article.html',
                'urlfetch': fetcher
                }
        doc = Document(html, **options)
        summary = doc.summary()
        with open('test_data/basic-multi-page-expected.html', 'r') as f:
            expected_html = f.read()
        diff_html = htmldiff(expected_html, summary.html)
        diff_doc = fragment_fromstring(diff_html)
        insertions = diff_doc.xpath('//ins')
        deletions = diff_doc.xpath('//del')
        if len(insertions) != 0:
            for i in insertions:
                print('unexpected insertion: %s' % i.xpath('string()'))
            self.fail('readability result does not match expected')
        if len(deletions) != 0:
            for i in deletions:
                print('unexpected deletion: %s' % i.xpath('string()'))
            self.fail('readability result does not match expected')

class TestIsSuspectedDuplicate(unittest.TestCase):

    def setUp(self):
        super(TestIsSuspectedDuplicate, self).setUp()
        with open('test_data/duplicate-page-article.html') as f:
            html = f.read()
            self._article = fragment_fromstring(html)

    def test_unique(self):
        with open('test_data/duplicate-page-unique.html') as f:
            html = f.read()
            page = fragment_fromstring(html)
        self.assertFalse(is_suspected_duplicate(self._article, page))

    def test_duplicate(self):
        with open('test_data/duplicate-page-duplicate.html') as f:
            html = f.read()
            page = fragment_fromstring(html)
        self.assertTrue(is_suspected_duplicate(self._article, page))

class TestSplitIntoParts(unittest.TestCase):

    def test_empty(self):
        elem = B.DIV()
        self.assertEquals(split_into_parts(elem), [])

    def test_initial_text(self):
        a_elem = B.A('world')
        elem = B.DIV('hello', a_elem)
        self.assertEquals(split_into_parts(elem), ['hello', a_elem])

    def test_interspersed(self):
        a_elem = B.A('world')
        h1_elem = B.H1('header')
        elem = B.DIV('hello', a_elem, '!- Jerry', h1_elem)
        expected = ['hello', a_elem, '!- Jerry', h1_elem]
        self.assertEquals(split_into_parts(elem), expected)

class TestMarkIfWhitespace(unittest.TestCase):

    def test_no_parts(self):
        parts = [B.BR(), B.BR()]
        self.assertEquals(mark_if_whitespace(parts, 0, 1), set())

    def test_some_text(self):
        parts = ['Hello', B.BR(), 'World', '', B.BR()]
        self.assertEquals(mark_if_whitespace(parts, 1, 3), set())

    def test_whitespace(self):
        parts = ['Hello', B.BR(), '\n', '', B.BR()]
        self.assertEquals(mark_if_whitespace(parts, 1, 4), {2, 3})

    def test_element(self):
        parts = ['Hello', B.BR(), '', B.A('World'), '', B.BR()]
        self.assertEquals(mark_if_whitespace(parts, 1, 5), set())

class TestSqueezeBreaks(unittest.TestCase):

    def _filter(self, parts, *args):
        return [p for i, p in enumerate(parts) if i not in args]

    def test_nothing_to_squeeze(self):
        parts = ['Hello', B.BR(), 'World', B.BR(), B.A(), B.BR()]
        self.assertEquals(squeeze_breaks(parts), parts)

    def test_one_whitespace_span(self):
        parts = ['Hello', B.BR(), '', '\t', B.BR(), B.A(), B.BR()]
        expected = self._filter(parts, 2, 3)
        self.assertEquals(squeeze_breaks(parts), expected)

    def test_two_whitespace_spans(self):
        parts = ['Hello', B.BR(), '', '\t', B.BR(), ' ', B.BR()]
        expected = self._filter(parts, 2, 3, 5)
        self.assertEquals(squeeze_breaks(parts), expected)

    def test_leading_whitespace(self):
        parts = [' ', B.BR()]
        self.assertEquals(squeeze_breaks(parts), parts)

class TestTransformDoubleBreaksIntoParagraphs(unittest.TestCase):

    def _read_test_doc(self, file_id):
        path = 'test_data/double-breaks-%s.html' % file_id
        with open(path, 'r') as f:
            html = f.read()
            return document_fromstring(html)

    def _test_one(self, test_id):
        original = test_id + '-original'
        expected = test_id + '-expected'
        doc = self._read_test_doc(original)
        transform_double_breaks_into_paragraphs(doc)
        expected_doc = self._read_test_doc(expected)
        doc_string = tostring(doc)
        expected_doc_string = tostring(expected_doc)
        if doc_string != expected_doc_string:
            diff = difflib.unified_diff(
                    expected_doc_string.splitlines(True),
                    doc_string.splitlines(True),
                    fromfile = 'expected',
                    tofile = 'actual'
                    )
            for line in diff:
                sys.stdout.write(line)
            self.fail('did not get expected result')

    def test_basic(self):
        self._test_one('basic')

    def test_some_headers(self):
        self._test_one('some-headers')

    def test_proper_paragraphs(self):
        self._test_one('proper-paragraphs')

    def test_mit(self):
        self._test_one('mit')

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--debug':
        del sys.argv[1]
        logging.basicConfig(level = logging.DEBUG)
    else:
        logging.basicConfig(level = logging.INFO)
    unittest.main()

if __name__ == '__main__':
    main()
