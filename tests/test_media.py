import unittest, io
class MediaTests(unittest.TestCase):
    def test_rejects_ssrf_and_video_urls(self):
        from media import safe_thumbnail
        for url in ['http://scontent.xx.fbcdn.net/a.jpg','https://localhost/a.jpg','https://127.0.0.1/a.jpg','https://evilfbcdn.net/a.jpg','https://scontent.xx.fbcdn.net/a.mp4','https://user:pass@scontent.xx.fbcdn.net/x','https://scontent.xx.fbcdn.net:8443/a.jpg']:
            self.assertFalse(safe_thumbnail(url),url)
        self.assertTrue(safe_thumbnail('https://scontent.xx.fbcdn.net/a.jpg?x=1'))
    def test_letterboxed_jpeg_meets_limits(self):
        from media import prepare_image
        from PIL import Image
        source=io.BytesIO(); Image.new('RGB',(20,80)).save(source,'PNG')
        data=prepare_image(source.getvalue()); img=Image.open(io.BytesIO(data))
        self.assertEqual(img.format,'JPEG'); self.assertEqual(img.size,(560,560))
