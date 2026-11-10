"""Fetch a hash-pinned erofs-utils source and extend noinline_data to symlinks."""
from pathlib import Path
import hashlib,io,json,sys,tarfile,urllib.request
URL='https://deb.debian.org/debian/pool/main/e/erofs-utils/erofs-utils_1.8.6.orig.tar.gz'
SHA='5b221dc3fd6d151425b30534ede46fb7a90dc233a8659cba0372796b0a066547'
OLD=b'if (!cfg.c_inline_data && S_ISREG(inode->i_mode)) {'
NEW=b'if (!cfg.c_inline_data &&\n\t\t    (S_ISREG(inode->i_mode) || S_ISLNK(inode->i_mode))) {'

def patch(source):
    if source.count(OLD)!=1:raise RuntimeError('Expected unique noinline_data regular-file condition')
    return source.replace(OLD,NEW,1)

def main():
    dest=Path(sys.argv[1]);dest.mkdir(parents=True,exist_ok=True)
    data=urllib.request.urlopen(URL,timeout=60).read()
    if hashlib.sha256(data).hexdigest()!=SHA:raise RuntimeError('erofs-utils source archive checksum mismatch')
    root=dest/'erofs-utils-1.8.6'
    if root.exists():raise RuntimeError('Source directory already exists')
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as t:t.extractall(dest,filter='data')
    file=root/'lib/inode.c';old=file.read_bytes();new=patch(old);file.write_bytes(new)
    report={'version':'1.8.6','source_url':URL,'archive_sha256':SHA,
        'file':'lib/inode.c','original_file_sha256':hashlib.sha256(old).hexdigest(),
        'patched_file_sha256':hashlib.sha256(new).hexdigest(),
        'scope':'noinline_data also applies to S_ISLNK; no change when inline_data is enabled'}
    (dest/'erofs-v41-builder.json').write_text(json.dumps(report,indent=2)+'\n')
    print('EROFS V41: ONE CONDITION PATCHED; HASH-PINNED SOURCE VERIFIED')
if __name__=='__main__':main()
