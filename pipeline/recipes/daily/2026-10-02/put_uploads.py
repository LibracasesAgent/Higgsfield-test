import json,sys,re,subprocess,os
res,srcdir,manifest=sys.argv[1],sys.argv[2],sys.argv[3]
j=json.load(open(res)); m=json.load(open(manifest)) if os.path.exists(manifest) else {}
for u in j["uploads"]:
    fn=re.search(r"@(\S+)",u["instructions"]).group(1)
    path=os.path.join(srcdir,fn)
    hdr=["-H",f"Content-Type: {u['content_type']}"]
    if "if-none-match" in u["upload_url"]: hdr+=["-H","If-None-Match: *"]
    code=subprocess.run(["curl","-sS","-o","/dev/null","-w","%{http_code}","-X","PUT",*hdr,"--data-binary","@"+path,u["upload_url"]],capture_output=True,text=True).stdout
    print(fn,code)
    if code=="200": m[fn]=dict(media_id=u["media_id"],url=u["url"])
json.dump(m,open(manifest,"w"),indent=1)
print(" ".join(m[k]["media_id"] for k in m if k in [re.search(r"@(\S+)",u["instructions"]).group(1) for u in j["uploads"]]))
