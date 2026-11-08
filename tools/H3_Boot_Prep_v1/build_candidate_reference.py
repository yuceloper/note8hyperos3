from pathlib import Path
import struct,gzip,hashlib,json,difflib
base=Path('analysis/h3-boot/preboot-analysis-v1');out=Path('out/H3_Boot_Prep_v1');b=(base/'boot.img').read_bytes()
assert hashlib.sha256(b).hexdigest()=='0cbc8b61b8e14e67ab7c2b4ce098504735c103e22b71c216e39db3dc740dcfa5'
u=lambda off:struct.unpack_from('<I',b,off)[0]
ks,rs,ss,page,version=u(8),u(16),u(24),u(36),u(40)
assert version==2 and page==4096 and ss==0
assert struct.unpack_from('<Q',b,1632)[0]==0
align=lambda n:(n+page-1)//page*page
ko=page;ro=align(ko+ks);so=align(ro+rs);do=align(so+ss);ds=u(1648)
k=b[ko:ko+ks];rd=b[ro:ro+rs];dt=b[do:do+ds]
def bootid(kernel,ramdisk,second,dtb):
 h=hashlib.sha1()
 for data in [kernel,ramdisk,second,b'',dtb]:h.update(data);h.update(struct.pack('<I',len(data)))
 return h.digest()
assert bootid(k,rd,b'',dt)==b[576:596], 'Source boot ID algorithm mismatch'
# Change only the fstab compatibility string; preserve the remainder of the DTB.
h=struct.unpack_from('>10I',dt);pos=h[2];strings=h[3];stack=[];changes=[];patched=bytearray(dt)
while True:
 token=struct.unpack_from('>I',dt,pos)[0];pos+=4
 if token==1:
  end=dt.index(b'\0',pos);stack.append(dt[pos:end].decode());pos=(end+4)&~3
 elif token==2:stack.pop()
 elif token==3:
  n,off=struct.unpack_from('>II',dt,pos);pos+=8;end=dt.index(b'\0',strings+off);name=dt[strings+off:end].decode()
  if '/'.join(stack)=='/firmware/android/fstab' and name=='compatible':
   assert dt[pos:pos+n]==b'android,fstab\0'
   new=b'android,xxxxx\0';assert len(new)==n
   patched[pos:pos+n]=new;changes.append(pos)
  pos=(pos+n+3)&~3
 elif token==4:pass
 elif token==9:break
 else:raise RuntimeError(token)
assert len(changes)==1
# Preserve all crypto settings, replace only system/vendor mount definitions.
original=(base/'fstab.qcom').read_text();lines=original.splitlines(True);modified=[];count=0
for line in lines:
 fields=line.split()
 if len(fields)>=5 and not line.lstrip().startswith('#') and fields[1] in ['/system','/vendor']:
  if fields[1]=='/system': line='/dev/block/by-name/system /system erofs ro wait,first_stage_mount\n'
  else: line='/dev/block/by-name/vendor /vendor ext4 ro,barrier=1 wait,first_stage_mount\n'
  count+=1
 modified.append(line)
assert count==2
fstab=''.join(modified).encode();(out/'fstab.emmc').write_bytes(fstab)
assert next(x for x in original.splitlines() if '/data ' in x)==next(x for x in fstab.decode().splitlines() if '/data ' in x)
(out/'fstab.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),fstab.decode().splitlines(True),fromfile='Lineage23-fstab.qcom',tofile='ginkgo-erofs-fstab.emmc')))
cpio=gzip.decompress(rd);pos=0;trailer=None;entries={};maxino=0
while pos+110<=len(cpio):
 start=pos;hdr=cpio[pos:pos+110];assert hdr[:6]==b'070701';v=[int(hdr[6+i*8:14+i*8],16) for i in range(13)];pos+=110;name=cpio[pos:pos+v[11]-1].decode();pos=(pos+v[11]+3)&~3;data=cpio[pos:pos+v[6]];pos=(pos+v[6]+3)&~3
 if name=='TRAILER!!!':trailer=start;break
 entries[name]=(v,data);maxino=max(maxino,v[0])
assert trailer is not None and 'fstab.emmc' not in entries
name=b'fstab.emmc\0';v=[maxino+1,0o100644,0,0,1,0,len(fstab),0,0,0,0,len(name),0]
entry=b'070701'+b''.join(f'{x:08x}'.encode() for x in v)+name
entry+=b'\0'*((-len(entry))%4);entry+=fstab;entry+=b'\0'*((-len(entry))%4)
newcpio=cpio[:trailer]+entry+cpio[trailer:];newcpio+=b'\0'*((-len(newcpio))%512)
newrd=gzip.compress(newcpio,compresslevel=9,mtime=0)
header=bytearray(b[:page]);struct.pack_into('<I',header,16,len(newrd));header[576:608]=bootid(k,newrd,b'',bytes(patched))+b'\0'*12
image=bytes(header)+k;image+=b'\0'*((-len(image))%page);newro=len(image);image+=newrd;image+=b'\0'*((-len(image))%page);newdo=len(image);image+=patched;image+=b'\0'*((-len(image))%page)
assert image[ko:ko+ks]==k and image[64:576]==b[64:576] and image[608:1632]==b[608:1632]
assert gzip.decompress(image[newro:newro+len(newrd)])==newcpio
assert image[newdo:newdo+ds]==bytes(patched)
assert bootid(k,newrd,b'',bytes(patched))==image[576:596]
assert len(image)<67108864
(out/'boot-ginkgo-h3-erofs-candidate.img').write_bytes(image)
meta={'status':'OFFLINE_VALIDATED_NOT_BOOT_TESTED','source_boot_sha256':hashlib.sha256(b).hexdigest(),'candidate_boot_sha256':hashlib.sha256(image).hexdigest(),'candidate_bytes':len(image),'kernel_preserved':True,'cmdline_preserved':True,'kernel_sha256':hashlib.sha256(k).hexdigest(),'fstab_sha256':hashlib.sha256(fstab).hexdigest(),'fstab_suffix':'emmc','dt_fstab_compatible_changed_to':'android,xxxxx','crypto_flags_preserved':True,'original_avb_footer_retained':False,'checks':['original boot SHA1 ID verified','new boot SHA1 ID verified','ramdisk decompress roundtrip','kernel byte comparison','cmdline byte comparison','DTB size preserved','fits 64 MiB boot partition'],'vintf_full_validation':False}
(out/'validation.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps(meta,indent=2))
