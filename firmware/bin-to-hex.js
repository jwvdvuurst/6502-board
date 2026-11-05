// Usage: node bin-to-hex.js input.bin 0400 > program.hex
const fs=require('fs');
const [file,address]=process.argv.slice(2);
if(!file || !/^[0-9a-f]{4}$/i.test(address||''))throw Error('Usage: node bin-to-hex.js input.bin 0400');
const bytes=fs.readFileSync(file),start=parseInt(address,16);
if(!bytes.length || start<0x400 || start+bytes.length>0x7800)throw Error('Program must fit in $0400-$77FF');
function record(a,data,type){
 const b=[data.length,a>>8,a&255,type,...data];b.push((-b.reduce((x,y)=>x+y,0))&255);
 return ':'+Buffer.from(b).toString('hex').toUpperCase();
}
const lines=[];
for(let i=0;i<bytes.length;i+=32)lines.push(record(start+i,bytes.subarray(i,i+32),0));
lines.push(record(0,[],1));
process.stdout.write(lines.join('\r\n')+'\r\n');
