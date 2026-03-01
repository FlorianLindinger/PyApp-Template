import time

while True:
    msg= input()
    if msg=="error":
        raise Exception("error")
    elif msg=="crash1":
        raise RuntimeError("intentional crash test")
    elif msg=="crash2":
        import os
        os._exit(1)
    elif msg=="crash3":
        import os
        os.abort()
    elif msg=="crash4":
        import ctypes
        ctypes.string_at(0)  # dereference NULL -> segfault on most platforms
    elif msg=="crash5":
        a = []
        while True:
            a.append(b"x" * 10_000_000)
    elif msg=="exit":
        break
    elif msg=="sleep":
        time.sleep(4)
        print(msg)
    
    else:
        print(msg)