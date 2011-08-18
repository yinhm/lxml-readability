from lxml.html import builder as B
from htmls import *
import sys
import unittest

class TestGetTitle(unittest.TestCase):

    def test_no_title(self):
        doc = B.HTML()
        self.assertEqual('', get_title(doc))

    def test_title(self):
        doc = B.HTML(
                B.HEAD(
                    B.TITLE('test title')
                    )
                )
        self.assertEqual('test title', get_title(doc))

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--debug':
        del sys.argv[1]
        logging.basicConfig(level = logging.DEBUG)
    else:
        logging.basicConfig(level = logging.INFO)
    unittest.main()

if __name__ == '__main__':
    main()
