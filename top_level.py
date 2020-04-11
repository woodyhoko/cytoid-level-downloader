import shutil
import requests
n = int(input("number of top levels : "))
rank = "https://cytoid.io/levels?sort=rating&order=desc&category=all&page="
s = requests.Session()
for i in range(1,10):
    r = s.get(rank+str(i))
    if r.status_code != 200:
        break
    for level in [x[6:-1] for x in r.content.decode().split() if 'href=\"/levels/' in x]:
        shutil.copy('./data/'+level.split('/')[-1]+".cytoidlevel", './top_level/'+level.split('/')[-1])
        n-=1
        if n==0:
            break
    if n==0:
        break
