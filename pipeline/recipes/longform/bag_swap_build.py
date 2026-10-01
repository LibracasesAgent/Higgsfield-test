import json, subprocess
def dur(f): return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f],capture_output=True,text=True).stdout)
# (audio piece, video shots[(src,start,weight,extra)], overlays at block start [(type,dict)])
P="1pwD5FXA8_dLwraTdrWKc0HJ8tZzzDD06.mp4"; KZ="1ftNQdXFnvgYmcLhN12OdbC0R3YQur16X.mp4"; IN="1StPro8S4b5_LUICHyivAkrFna1M1k3ao.mp4"
ZP="1CcakagPN5oiWEneKORpvJblnPYnQvWHI.mp4"; WK="1MtOonVbf-pqmrcU5DUgY6995LObDfwn7.mp4"; CF="1Mtx32enLMlOkpIfl_Cr1EYezTdody3E1.mp4"
blocks=[
 # hook: transformation clip with its own whoosh/zip sound, narration over it
 (("mix","transform.mp4",1.9,6.5,"l1.mp3",0.3), [("transform.mp4",1.9,0.674,{}),("f_tidy.png",0,0.326,dict(zoom=[1.0,1.06]))], [("label",dict(text="THE BAG SWAP",dur=1.8,y=300))]),
 (("nar","l2.mp3"), [("oldbag.mp4",0.3,1,dict(fx="bw",zoom=[1.0,1.08])),("f_mess.png",0,1,dict(fx="bw",zoom=[1.0,1.12]))], []),
 (("nar","l3.mp3"), [("f_tidy.png",0,1,dict(zoom=[1.12,1.0]))], []),
 (("nar","l4.mp3"), [("shotA_gate.mp4",0,0.45,dict(speed=1.4)),(P,3.6,0.55,dict(focus=[0.5,0.45]))], [("tag",dict(text="PASSPORT → BACK POCKET",dur=3.6))]),
 (("nar","l5.mp3"), [(KZ,8.0,1,{})], [("tag",dict(text="KEYS → GOLD SIDE ZIP",dur=2.8))]),
 (("src","testi_black.mp4",34.9,40.45), [("testi_black.mp4",34.9,0.4,{}),("black_detail.mp4",5.0,0.6,{})], []),
 (("nar","l6.mp3"), [(IN,0.3,1,{}),(IN,5.0,1,{}),(IN,8.5,1,{})], [("tag",dict(text="EVERYTHING ELSE → MAIN ZIP",dur=4.0,size=54))]),
 (("src","testi_black.mp4",56.9,65.65), [("testi_black.mp4",56.9,0.35,{}),("black_detail.mp4",9.5,0.35,{}),("testi_black.mp4",63.3,0.3,{})], []),
 (("src",ZP,0.0,1.7), [(ZP,0.0,1,dict(zoom=[1.0,1.08]))], [("tag",dict(text="ZIPPED. DONE.",dur=1.7))]),
 (("nar","l7.mp3"), [(WK,0.5,1,{})], [("review",dict(n=10,dur=3.8,y=330))]),
 (("nar","l8.mp3"), [(WK,8.0,0.5,{}),(CF,1.0,0.5,dict(focus=[0.3,0.55]))], [("review",dict(n=3,dur=3.6,y=330))]),
 (("src","k_cta.mp4",0.1,4.9), [("k_cta.mp4",0.1,1,{})], []),
]
pieces=[]; segs=[]; ov=[]; t=0.0
for aud, shots, ovs in blocks:
    if aud[0]=="nar": L=dur(aud[1])+0.3
    elif aud[0]=="mix": L=aud[3]-aud[2]
    else: L=round(aud[3]-aud[2],3)
    pieces.append((aud,L))
    for typ,o in ovs: ov.append(dict(type=typ, at=round(t+0.05,2), **o))
    ws=sum(s[2] for s in shots)
    for src,st,w,ex in shots: segs.append(dict(src=src,start=st,dur=round(L*w/ws,3),mute=True,**ex))
    t+=L
ov.append(dict(type="end",title="Everything has a spot.",sub="Tap the link below",at=round(t-2.4,2),dur=2.4))
inputs=[]; fc=[]; k=0; labels=[]
for aud,L in pieces:
    if aud[0]=="nar":
        inputs+=["-i",aud[1]]; fc.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={L:.3f},atrim=0:{L:.3f}[p{k}]"); labels.append(f"[p{k}]"); k+=1
    elif aud[0]=="src":
        inputs+=["-i",aud[1]]; fc.append(f"[{k}:a]atrim={aud[2]}:{aud[3]},asetpts=N/SR/TB,aresample=48000,aformat=channel_layouts=stereo,afade=t=in:d=0.03,afade=t=out:st={L-0.05:.3f}:d=0.05[p{k}]"); labels.append(f"[p{k}]"); k+=1
    else:  # clip sound (whoosh/zip) at 0.5 under narration
        inputs+=["-i",aud[1],"-i",aud[4]]; ms=int(aud[5]*1000)
        fc.append(f"[{k}:a]atrim={aud[2]}:{aud[3]},asetpts=N/SR/TB,aresample=48000,aformat=channel_layouts=stereo,volume=0.6[c{k}];[{k+1}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[n{k}];[c{k}][n{k}]amix=inputs=2:normalize=0:duration=longest,apad=whole_dur={L:.3f},atrim=0:{L:.3f}[p{k}]")
        labels.append(f"[p{k}]"); k+=2
fc.append("".join(labels)+f"concat=n={len(labels)}:v=0:a=1,loudnorm=I=-16[o]")
subprocess.run(["ffmpeg","-hide_banner","-loglevel","error",*inputs,"-filter_complex",";".join(fc),"-map","[o]","-y","swap_audio.wav"],check=True)
edl=dict(audio="mute",vo="swap_audio.wav",vo_start=0.0,bed_gain=0.0,segments=segs,overlays=ov,caption_y=1010,
         keywords=["bottomless","keys","passport","back","gold","zip","both","sides","pockets","room","everything","spot","nothing","many"])
json.dump(edl,open("swap.json","w"),indent=1)
print("total",round(t,2),"segments",len(segs),"overlays",len(ov))
