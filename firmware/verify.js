const fs=require('fs'),assert=require('assert');
const crypto=require('crypto');
const rom=fs.readFileSync('build/rom.bin');
assert.equal(rom.length,8192);
for(const o of [0x1ffa,0x1ffc,0x1ffe]) {
 const a=rom.readUInt16LE(o); assert(a>=0xe000 && a<0xfffa);
}
for(let o=0;o<15;o+=3) assert.equal(rom[o],0x4c);
const eprom=Buffer.alloc(32768,255);rom.copy(eprom);
fs.writeFileSync('build/eprom32k.bin',eprom);
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
fs.writeFileSync('build/images.json',JSON.stringify({rom:{file:'rom.bin',bytes:rom.length,cpuBase:'E000',sha256:hash(rom)},eprom:{file:'eprom32k.bin',bytes:eprom.length,imageOffset:0,sha256:hash(eprom)}},null,2)+'\n');
console.log('Verified 8192-byte ROM, vectors and API; wrote 32768-byte EPROM image (ROM in first 8 KiB).');
