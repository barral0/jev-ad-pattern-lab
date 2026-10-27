"""Still-image only, bounded, public CDN fetches. Never follows redirects."""
import io, re, socket, ipaddress, shutil
from urllib.parse import urlsplit
from PIL import Image, ImageOps
from pathlib import Path
import os
import httpx
MAX_BYTES=8*1024*1024

def safe_thumbnail(url):
    if not isinstance(url,str): return False
    try:
        p=urlsplit(url); host=(p.hostname or '').lower()
        return p.scheme=='https' and p.port in (None,443) and not p.username and not p.password and any(host.endswith('.'+d) for d in ('fbcdn.net','fbsbx.com')) and not re.search(r'\.(mp4|webm|mov|m3u8)(\?|$)',url,re.I)
    except ValueError: return False

def validate_public_dns(url):
    if not safe_thumbnail(url): raise ValueError('Not an approved HTTPS still thumbnail')
    addresses=socket.getaddrinfo(urlsplit(url).hostname,443,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(x[4][0]).is_global for x in addresses): raise ValueError('Private or reserved address blocked')
    return addresses[0][4][0]

async def fetch_thumbnail(url,transport=None):
    address=validate_public_dns(url)
    original=urlsplit(url)
    # Pin the checked IP so a DNS rebind cannot change the destination after validation.
    target=httpx.URL(url).copy_with(host=address)
    async with httpx.AsyncClient(follow_redirects=False,timeout=20,trust_env=False,transport=transport) as client:
        async with client.stream('GET',target,headers={'Host':original.hostname},extensions={'sni_hostname':original.hostname}) as response:
            if 300<=response.status_code<400: raise ValueError('Redirects are disabled')
            response.raise_for_status()
            if response.status_code!=200: raise ValueError('Unexpected thumbnail response')
            if response.headers.get('content-type','').split(';')[0] not in ('image/jpeg','image/png'): raise ValueError('Only JPEG/PNG accepted')
            chunks=bytearray()
            async for chunk in response.aiter_bytes():
                chunks.extend(chunk)
                if len(chunks)>MAX_BYTES: raise ValueError('Thumbnail exceeds size limit')
            return prepare_image(bytes(chunks))

def prepare_image(data):
    if len(data)>MAX_BYTES: raise ValueError('Image too large')
    with Image.open(io.BytesIO(data)) as image:
        if image.format not in ('PNG','JPEG') or getattr(image,'is_animated',False): raise ValueError('Still PNG/JPEG required')
        if image.width*image.height>25_000_000: raise ValueError('Image pixel limit')
        image=ImageOps.exif_transpose(image).convert('RGB')
        image=ImageOps.pad(image,(560,560),method=Image.Resampling.LANCZOS,color='white')
        buffer=io.BytesIO(); image.save(buffer,'JPEG',quality=85); return buffer.getvalue()

def find_tesseract():
    command = shutil.which('tesseract')
    if command:
        return command
    candidates = [
        Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Tesseract-OCR' / 'tesseract.exe',
        Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / 'Tesseract-OCR' / 'tesseract.exe',
        Path.home() / 'AppData' / 'Local' / 'Programs' / 'Tesseract-OCR' / 'tesseract.exe',
    ]
    return next((str(p) for p in candidates if p.is_file()), None)


def ocr_status():
    return 'available' if find_tesseract() else 'unavailable: install Tesseract and add it to PATH'


def local_ocr(data):
    command = find_tesseract()
    if not command: return {'status':'unavailable','text':None}
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = command
        text=pytesseract.image_to_string(Image.open(io.BytesIO(data)),timeout=15).strip()
        return {'status':'available','text':text}
    except Exception as exc: return {'status':'error','text':None,'error':type(exc).__name__}
