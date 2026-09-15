import unittest
from filename_tokens import generator_token


class Tests(unittest.TestCase):
    def test_observed_vc_prefix(self):
        token='0015c714-5c20-5766-8944-540102ec090f'
        self.assertEqual(generator_token('vc-'+token+'.mp4'),generator_token('ms-'+token+'.mp4'))
        self.assertEqual(generator_token('vc2-'+token+'.mp4'),token)

    def test_preserve_unrecognized(self):
        self.assertEqual(generator_token('other-token.mp4'),'other-token')

    def test_no_uuid_mangling(self):
        self.assertEqual(generator_token('ms-a-b-c.mp4'),'a-b-c')


if __name__=='__main__':unittest.main()
