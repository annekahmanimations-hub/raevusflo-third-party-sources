#!/usr/bin/env python3
"""Download and verify immutable source archives for Vosk candidate rebuild."""
import hashlib, json, pathlib, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / 'sources.json'

def check_sha256(path, expected_sha):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower() == expected_sha.lower()

def download_and_verify(item, out_dir):
    dest = out_dir / item['file']
    if dest.exists() and check_sha256(dest, item['sha256']):
        print(f"PASS (cached): {item['file']}")
        return dest
        
    print(f"Downloading {item['name']} from {item['url']}...")
    tmp = dest.with_suffix(dest.suffix + '.tmp')
    req = urllib.request.Request(item['url'], headers={'User-Agent': 'Vosk-CI-Rebuild/1.0'})
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, 'wb') as out:
        while chunk := resp.read(65536):
            out.write(chunk)
            
    if not check_sha256(tmp, item['sha256']):
        tmp.unlink()
        raise ValueError(f"Checksum mismatch for {item['file']}")
        
    tmp.replace(dest)
    print(f"PASS (downloaded): {item['file']}")
    return dest

def main():
    out_dir = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else (ROOT / 'sources')
    out_dir.mkdir(parents=True, exist_ok=True)
    sources = json.loads(MANIFEST_PATH.read_text(encoding='utf8'))
    print(f"Verifying/downloading {len(sources)} source archives to {out_dir}...")
    for item in sources:
        download_and_verify(item, out_dir)
    print("All source archives verified successfully.")

if __name__ == '__main__':
    main()
