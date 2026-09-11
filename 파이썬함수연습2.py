#파이썬함수연습2.py
def connetURI(server,port):
    #f-string은 변수명을 바로 넘김
    strURL = f"http://{server}:{port}"
    return strURL

print(connetURI("kpc.com",8080)) 