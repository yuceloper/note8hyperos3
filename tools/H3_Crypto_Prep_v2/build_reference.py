from pathlib import Path
import struct,gzip,hashlib,json,difflib
src=Path('out/H3_Boot_Prep_v1');out=Path('out/H3_Crypto_Prep_v2');b=(src/'boot-ginkgo-h3-erofs-candidate.img').read_bytes()
sha=lambda d:hashlib.sha256(d).hexdigest()
assert sha(b)=='1ba87fc1cea2f3a0b9df4a616633d43dc776e28a5ee9acb588511ac3fd6a1c41'
old=(src/'fstab.emmc').read_bytes();lines=old.splitlines(keepends=True);changes=0
for i,line in enumerate(lines):
 f=line.split()
 if len(f)>1 and f[1]==b'/data':
  assert line.count(b'+wrappedkey_v0')==1 and line.count(b':wrappedkey_v0')==1
  lines[i]=line.replace(b'+wrappedkey_v0',b'').replace(b':wrappedkey_v0',b'');changes+=1
assert changes==1
new=b''.join(lines)
assert b'fileencryption=aes-256-xts:aes-256-cts:v2+emmc_optimized,' in new
assert b'metadata_encryption=aes-256-xts,' in new
(out/'fstab.emmc').write_bytes(new)
u=lambda o:struct.unpack_from('<I',b,o)[0]
ks,rs,ss,page,ds=u(8),u(16),u(24),u(36),u(1648);assert u(40)==2 and ss==0 and page==4096
align=lambda n:(n+page-1)//page*page
ro=align(page+ks);do=align(ro+rs);k=b[page:page+ks];dt=b[do:do+ds]
c=gzip.decompress(b[ro:ro+rs]);p=0;rebuilt=b'';found=0;trailer=None
while p+110<=len(c):
 start=p;h=bytearray(c[p:p+110]);assert h[:6]==b'070701';v=[int(h[6+j*8:14+j*8],16) for j in range(13)];p+=110;name=c[p:p+v[11]-1].decode();p=(p+v[11]+3)&~3;datapos=p;data=c[p:p+v[6]];p=(p+v[6]+3)&~3
 if name=='TRAILER!!!':trailer=start;break
 if name=='fstab.emmc':
  assert data==old;found+=1
  h[54:62]=f'{len(new):08x}'.encode()
  entry=bytes(h)+c[start+110:datapos]+new;entry+=b'\0'*((-len(entry))%4);rebuilt+=entry
 else:rebuilt+=c[start:p]
assert found==1 and trailer is not None
rebuilt+=c[trailer:];rebuilt+=b'\0'*((-len(rebuilt))%512)
rd=gzip.compress(rebuilt,compresslevel=9,mtime=0)
def bootid(k,r,dt):
 h=hashlib.sha1()
 for data in [k,r,b'',b'',dt]:h.update(data);h.update(struct.pack('<I',len(data)))
 return h.digest()
assert bootid(k,b[ro:ro+rs],dt)==b[576:596]
h=bytearray(b[:page]);struct.pack_into('<I',h,16,len(rd));h[576:608]=bootid(k,rd,dt)+b'\0'*12
image=bytes(h)+k;image+=b'\0'*((-len(image))%page);rpos=len(image);image+=rd;image+=b'\0'*((-len(image))%page);dpos=len(image);image+=dt;image+=b'\0'*((-len(image))%page)
assert image[page:page+ks]==k and image[dpos:dpos+ds]==dt
assert image[64:576]+image[608:1632]==b[64:576]+b[608:1632]
assert gzip.decompress(image[rpos:rpos+len(rd)])==rebuilt
assert len(image)<67108864
# Independently reparse the resulting cpio and verify its fstab.
p=0;found=0
while p+110<=len(rebuilt):
 h=rebuilt[p:p+110];v=[int(h[6+j*8:14+j*8],16) for j in range(13)];p+=110;name=rebuilt[p:p+v[11]-1].decode();p=(p+v[11]+3)&~3;data=rebuilt[p:p+v[6]];p=(p+v[6]+3)&~3
 if name=='TRAILER!!!':break
 if name=='fstab.emmc':assert data==new;found+=1
assert found==1
(out/'boot-ginkgo-h3-standardkeys-v2.img').write_bytes(image)
(out/'fstab.diff').write_text(''.join(difflib.unified_diff(old.decode().splitlines(True),new.decode().splitlines(True),fromfile='v1',tofile='standardkeys-v2')))
meta={'status':'OFFLINE_VALIDATED_NOT_BOOT_TESTED','previous_fstab_sha256':sha(old),'fstab_sha256':sha(new),'boot_sha256':sha(image),'boot_bytes':len(image),'kernel_and_dtb_preserved_from_v1':True,'cmdline_preserved':True,'data_change':'Remove only wrappedkey_v0 flags; retain FBE v2, inlinecrypt and metadata encryption','existing_userdata_compatibility':'NOT_PROVEN; Android17-to-16 app/framework data compatibility not tested','full_vintf_validation':False}
(out/'validation.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta,indent=2))
