import getpass
import requests
pages = int(input("pages to download (from latest) : "))
forcemode = 0 if input("stop when reached downloaded content? (y/n)") == 'y' else 1
s = requests.Session()
username = input("username : ")
password = getpass.getpass("password : ")
account = {"username":username,"password":password,"remember":"true","token":"fuckcensorship"}
cook_request = s.post("https://api.cytoid.io/session",data=account)
cooky = dict([[x[:11],x[12:].split(';')[0]] if x[12]=='=' else [x[:15],x[16:].split(';')[0]] for x in cook_request.headers['Set-Cookie'].split(', ') if x[:11]=='cytoid:sess'])

download_link = "https://cytoid.io/levels?sort=creation_date&order=desc&category=all&page="
for i in range(1,pages):
    print('page',i)
    r = s.get(download_link+str(i))
    if r.status_code != 200:
        print('page',i,'error')
        if forcemode:
            continue
        break
    for level in [x[6:-1] for x in r.content.decode().split() if 'href=\"/levels/' in x]:
        try:
            f = open('./data/'+level.split('/')[-1]+".cytoidlevel",'r')
            f.close()
            print('file_existed')
            continue
        except:
            r = s.get("https://api.cytoid.io"+level+"/package", cookies = cooky)
            f = open('./data/'+level.split('/')[-1]+".cytoidlevel",'wb')
            f.write(r.content)
            f.close()
            print('successfully download',level.split('/')[-1])
