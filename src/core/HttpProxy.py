#coding=utf-8
__author__ = 'ding'
import sys
import json
import BaseHTTPServer
import urllib2
from urllib2 import HTTPError
import threading
from SocketServer import ThreadingMixIn
import socket


class RedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_301(self, req, fp, code, msg, headers):
        pass
    def http_error_302(self, req, fp, code, msg, headers):
        pass
    def http_error_303(self, req, fp, code, msg, headers):
        pass
    def http_error_307(self, req, fp, code, msg, headers):
        pass

urllib2.install_opener(urllib2.build_opener(RedirectHandler))


class Handle(BaseHTTPServer.BaseHTTPRequestHandler):

    def __write_success(self,ret):
        request = {}
        request['method'] = self.command
        request['path'] = self.path
        request['headers'] = dict(self.headers)

        response = {}
        response['code'] = ret.getcode()
        response['headers'] = dict(ret.headers)

        data = {'request':request,'response':response,'suc':0}
        sys.stdout.write(json.dumps(data)+'\n')

    def __write_fail(self,ret,msg):
        request = {}
        request['method'] = self.command
        request['path'] = self.path
        request['headers'] = self.headers
        data = {'request':request,'response':None,'suc':-1,'msg':msg}

        sys.stderr.writelines(json.dumps(data))

    def __write_response(self,ret):
        #输出到控制台
        self.__write_success(ret)
        #完成代理任务，数据写回
        self.send_response(ret.getcode())
        for key in ret.headers.keys():
            if key == 'transfer-encoding' and ret.headers['transfer-encoding'] == 'chunked' and \
                ret.headers.get('content-encoding','') == 'gzip':
                print '==== skip chunked header!!!!'
                continue
            self.send_header(key,ret.headers[key])
        self.end_headers()
        BUFFER_SIZE = 1024
        data = ret.read(BUFFER_SIZE)


        #处理 chunked 传输编码
        if ret.headers.get('transfer-encoding','') == 'chunked' and \
            ret.headers.get('content-encoding','') != 'gzip':
            while data:
                size = len(data)
                print '===chunked size:',size,hex(size).upper()[2:]
                self.wfile.write('%s\r\n'%hex(size).upper()[2:])
                self.wfile.write(data)
                self.wfile.write('\r\n')
                data = ret.read(BUFFER_SIZE)
            self.wfile.write('0\r\n\r\n')

        else:
            while data:
                self.wfile.write(data)
                data = ret.read(BUFFER_SIZE)


    def do_GET(self):
        print 'raw requestline:',self.raw_requestline
        try:
            req = urllib2.Request(self.path,headers=self.headers)
            ret = urllib2.urlopen(req)
        except HTTPError,e:
            ret = e
        self.__write_response(ret)



    def do_POST(self):
        content_length = int(self.headers['content-length'])
        data = self.rfile.read(content_length)
        try:
            req = urllib2.Request(self.path,data,headers=self.headers)
            ret = urllib2.urlopen(req)
        except HTTPError,e:
            ret = e
        self.__write_response(ret)



    def do_CONNECT(self):

        print self.protocol_version

        self.send_response(200)
        self.end_headers()

        #self.wfile.write('HTTP/1.1 200 OK\r\n\r\n')

        soc = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        host,port = self.path.split(':')
        port = int(port)
        print (host,port)
        print 'raw requestline:',self.raw_requestline
        soc.connect((host,port))
        soc_fd = soc.makefile('rw', 0)
        t1 = threading.Thread(target=self._https_forward, args=(self.connection, soc, 'browser -> server'))
        t2 = threading.Thread(target=self._https_forward, args=(soc, self.connection, 'server -> browser'))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    def _https_forward(self, soc1, soc2, description):
        print description, 'started!!'
        BUFFER_SIZE = 1024
        data = soc1.recv(BUFFER_SIZE)
        while data:
            #print description, 'data:\n',data
            soc2.sendall(data)
            data = soc1.recv(BUFFER_SIZE)
        print description, 'down!!'



class ThreadHttpServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
    pass



def main():

    server = ThreadHttpServer(('',9876),Handle)
    server.serve_forever()


if __name__ == '__main__':
    main()