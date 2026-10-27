"""Creative identity must survive signed, expiring CDN URLs. Synthetic fixtures only."""
import unittest

from labcore import Ad, fingerprint


def ad(ad_id, url, copy='same copy', media_ids=None):
    return Ad(ad_id=ad_id, page_id='1', copy=copy, thumbnail_url=url, media_ids=media_ids or [])


FILE = 'https://scontent.xx.fbcdn.net/v/t39.1-6/111_222_n.jpg'


class StableFingerprintTests(unittest.TestCase):
    def test_signed_query_parameters_do_not_change_identity(self):
        a = ad('1', FILE + '?stp=dst-jpg&oh=00_first&oe=AAA')
        b = ad('1', FILE + '?stp=dst-jpg&oh=00_second&oe=BBB')
        self.assertEqual(fingerprint(a), fingerprint(b))

    def test_cdn_edge_host_does_not_change_identity(self):
        a = ad('1', FILE + '?oh=1')
        b = ad('1', FILE.replace('scontent.xx', 'scontent.yy') + '?oh=2')
        self.assertEqual(fingerprint(a), fingerprint(b))

    def test_different_image_files_stay_distinct(self):
        a = ad('1', FILE)
        b = ad('2', FILE.replace('111_222', '333_444'))
        self.assertNotEqual(fingerprint(a), fingerprint(b))

    def test_same_image_with_different_copy_stays_distinct(self):
        self.assertNotEqual(fingerprint(ad('1', FILE, copy='one')), fingerprint(ad('2', FILE, copy='two')))

    def test_missing_media_identity_never_merges_unrelated_ads(self):
        self.assertNotEqual(fingerprint(ad('1', None)), fingerprint(ad('2', None)))

    def test_explicit_media_ids_take_priority_over_url(self):
        a = ad('1', FILE + '?oh=1', media_ids=['m1'])
        b = ad('2', 'https://other.fbcdn.net/x.jpg', media_ids=['m1'])
        self.assertEqual(fingerprint(a), fingerprint(b))


if __name__ == '__main__':
    unittest.main()
