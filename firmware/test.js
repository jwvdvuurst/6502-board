// Instruction-level integration test; VIA/Pico modeled, not electrical timing.
const fs=require('fs'), assert=require('assert');
const {CPU6502}=require('./tools/cpu6502/compiled/cpu6502');
const ReadWrite={read:0,write:1};
const WAIT=Symbol('waiting for keyboard');
function machine(input,options={}) {
 const ram=Buffer.alloc(262144,options.fill||0),rom=fs.readFileSync(__dirname+'/build/rom.bin');
 const io=Buffer.alloc(16),keys=[...Buffer.from(input)],frames=[];
 let bank=0,ack=false,request=false,pending=false,frame=[],transfers=0;
 const display=Buffer.alloc(2000,32);
 let escaped=false;
 function output(byte){
  if(byte===0xc0){
   if(frame.length){processRecord();frame=[];}
   escaped=false;return;
  }
  if(byte===0xdb){escaped=true;return;}
  if(escaped){assert(byte===0xdc||byte===0xdd);byte=byte===0xdc?0xc0:0xdb;escaped=false;}
  frame.push(byte);
 }
 function processRecord(){
  const length={1:2003,2:4,3:3}[frame[0]];assert(length,'unknown display opcode');
  assert.equal(frame.length,length,'invalid display record length');
  if(frame[0]===1){display.set(frame.slice(1,2001));assert(frame[2001]+256*frame[2002]<2000);}
  if(frame[0]===2){const offset=frame[1]+256*frame[2];assert(offset<2000);display[offset]=frame[3];}
  if(frame[0]===3){assert(frame[1]+256*frame[2]<2000);}
  if(frame[0]!==2)frames.push(display.toString());
 }
 function edge(high) {
  if(ack===high)return;
  ack=high;
  if(Boolean(io[12]&16)===high)io[13]|=16;
 }
 const accessMemory=(rw,a,v)=>{
  a&=65535;
  if(a>=0xe000) {assert.equal(rw,ReadWrite.read,'write to ROM');return rom[a-0xe000];}
  if(a>=0xc000 && a<0xc100){if(rw===1)bank=v&15;return 0;}
  if(a>=0xc100 && a<0xc200){
   const r=a&15;
   if(rw===0){
    if(r===13 && pending){
     if(io[15]&1){if(!keys.length)throw WAIT;io[0]=keys.shift();}
     else {
      output(io[0]);
     }
     pending=false;edge(true);transfers++;
    }
    const result=io[r]; if(r===0)io[13]&=~16;return result;
   }
   if(r===13){io[13]&=~v;return;}
   if(r===12){
    io[r]=v;const req=((v>>1)&7)===7;
    if(req&&!request){assert(!ack,'request before ACK release');assert.equal(io[2],(io[15]&1)?0:255);pending=true;}
    if(!req&&request){assert(ack,'request dropped before ACK');edge(false);}
    request=req;return;
   }
   io[r]=v;return;
  }
  if(a>=0xc000)throw Error('undefined I/O '+a.toString(16));
  const physical=a<0x8000?a:bank*16384+(a&16383);
  if(rw===0)return ram[physical];
  ram[physical]=v;
 };
 const cpu=new CPU6502({flavor:'wdc65c02'});
 cpu.addPageHandler({start:()=>0,end:()=>255,read:(p,o)=>accessMemory(0,(p<<8)|o),write:(p,o,v)=>accessMemory(1,(p<<8)|o,v)});
 cpu.reset();
 let steps=0;
 try {
  for(;steps<15000000;steps++){
   cpu.step();
  }
  throw Error('instruction budget exceeded PC='+cpu.getState().pc.toString(16));
 }catch(e){if(e!==WAIT){console.error('PC',cpu.getState().pc.toString(16),'screen',ram.subarray(0x7800,0x7fd0).toString());throw e;}}
 assert.equal(keys.length,0);assert.equal(frame.length,0,'truncated frame');
 assert.deepEqual(display,ram.subarray(0x7800,0x7fd0),'Pico display differs from SRAM screen');
 return {ram,frames,bank,steps,transfers,screen:ram.subarray(0x7800,0x7fd0).toString()};
}
function ihex(addr,data,type=0){const b=[data.length,addr>>8,addr&255,type,...data];b.push((-b.reduce((a,b)=>a+b,0))&255);return ':'+Buffer.from(b).toString('hex').toUpperCase()+'\r';}
let m=machine('H\rK 000F\rD 0400\r');
assert(m.screen.includes('G AAAA'));assert.equal(m.bank,15);assert(m.screen.includes('00 00 00'));
console.log('PASS reset, monitor help, bank latch, memory dump, full screen frames and four-phase handshake');
const program=[0xa9,0x55,0x8d,0x00,0x05,0x60];
m=machine('L\r'+ihex(0x400,program)+ihex(0,[],1)+'G 0400\r');
assert.deepEqual([...m.ram.subarray(0x400,0x406)],program);assert.equal(m.ram[0x500],0x55);
console.log('PASS checked Intel HEX loading, program execution and RTS return');
for(const record of [ihex(0x7800,[42]),ihex(0x3ff,[42]),ihex(0x77ff,[42,43]),':010400002A00\r',ihex(0x400,[1],2)]){
 m=machine('L\r'+record);assert(m.screen.includes('LOAD ERROR'));assert.equal(m.ram[0x400],0);
}
console.log('PASS loader checksum, type, workspace and screen-boundary rejection');
m=machine('B\r10 LET A=6*7\r20 PRINT A\r30 END\rLIST\rRUN\rEXIT\r');
assert(m.frames.some(f=>f.includes('42')));assert(m.screen.includes('20 PRINT A'));assert(m.screen.trimEnd().endsWith('>'));
console.log('PASS ROM BASIC cold start, line storage, LIST, arithmetic, RUN, EXIT');
m=machine('B\rPRINT 123\r\x1bH\r');assert(m.frames.some(f=>f.includes('123')));assert(m.screen.includes('G AAAA'));
console.log('PASS BASIC immediate execution and Escape to monitor');
m=machine('H\r'.repeat(10));assert(m.screen.includes('G AAAA'));assert.equal(m.ram[0x7fd0],0);
console.log('PASS screen scrolling and unused screen tail preservation');
m=machine('B\rPRINT 42\rEXIT\r',{fill:0xa5});assert(m.frames.some(f=>f.includes('42')));assert.equal(m.ram[0x7fd0],0xa5);
console.log('PASS cold start with uninitialized RAM');
m=machine('B\rREM '+('X'.repeat(150))+'\rPRINT 7\rEXIT\r');assert(m.frames.some(f=>f.includes('7')));
console.log('PASS overlong BASIC input remains within its line buffer');
m=machine('L\r'+fs.readFileSync(__dirname+'/build/hello.hex','utf8')+'G 0400\r');assert(m.screen.includes('HELLO FROM A LOADED PROGRAM!'));
console.log('PASS assembled sample program through generated Intel HEX');
