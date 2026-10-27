import unittest, asyncio
from unittest.mock import patch
import httpx, io
from PIL import Image
class FetchSecurityTests(unittest.TestCase):
    def test_dns_is_pinned_and_original_hostname_used_for_tls(self):
        from media import fetch_thumbnail
        source=io.BytesIO();Image.new('RGB',(280,280)).save(source,'PNG')
        seen=[]
        def handler(request):
            seen.append(request)
            return httpx.Response(200,headers={'Content-Type':'image/png'},content=source.getvalue())
        with patch('media.socket.getaddrinfo',return_value=[(2,1,6,'',('8.8.8.8',443))]):
            result=asyncio.run(fetch_thumbnail('https://scontent.xx.fbcdn.net/p.png',transport=httpx.MockTransport(handler)))
        self.assertTrue(result)
        self.assertEqual(seen[0].url.host,'8.8.8.8')
        self.assertEqual(seen[0].headers['Host'],'scontent.xx.fbcdn.net')
        self.assertEqual(seen[0].extensions['sni_hostname'],'scontent.xx.fbcdn.net')
    def test_private_dns_and_redirect_are_denied(self):
        from media import fetch_thumbnail
        with patch('media.socket.getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]):
            with self.assertRaises(ValueError): asyncio.run(fetch_thumbnail('https://scontent.xx.fbcdn.net/a.jpg'))
        def redirect(request): return httpx.Response(302,headers={'Location':'http://127.0.0.1/secret'})
        with patch('media.socket.getaddrinfo',return_value=[(2,1,6,'',('8.8.8.8',443))]):
            with self.assertRaises(ValueError): asyncio.run(fetch_thumbnail('https://scontent.xx.fbcdn.net/a.jpg',transport=httpx.MockTransport(redirect)))
