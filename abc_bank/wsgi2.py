# -*- coding: utf-8 -*-
from server1 import app
from cheroot.wsgi import Server as WSGIServer

if __name__ == '__main__':
    # app.run(host='0.0.0.0', port=8899, threaded=True)
    server = WSGIServer(bind_addr=('0.0.0.0', 9000), wsgi_app=app, numthreads=30)
    server.start()