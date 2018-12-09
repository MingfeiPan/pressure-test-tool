#-*- coding: utf-8 -*-
#
from gevent import monkey
monkey.patch_all()

import gevent
import sys
import requests
import argparse
import socket
import time
from gevent.pool import Pool
# from urllib3.util import url
from requests import RequestException
from collections import defaultdict, namedtuple


http_methods = ['GET', 'POST', 'DELETE', 'PATCH', 'PUT']
data_methods = ['POST', 'PATCH', 'PUT']
# default_timeout = 60

ret = {'error':[], 'msg': defaultdict(list), 'total_time': 0}
stats = namedtuple('stats', ['count', 'total_time', 'rps', 'avg', 'min', 'max'])

class Tools(object):

	def __init__(self):
		pass

	def call(self, method, url, **params):

		start = time.time()
		try:
			result = method(url, **params)
		except Exception as e:
			ret['error'].append(e)
		else:
			duration = time.time() - start
			ret['msg'][result.status_code].append(duration)

	def run(self, url, requests_total, concurrency, duration, method,data, auth, headers=None):

		if requests_total is None:
			print('running for {} seconds with concurrency {}'.format(duration, concurrency))
		else:
			print('running for {} queries with concurrency {}'.format(requests_total, concurrency))

		start = time.time()
		print("start!")

		method = getattr(requests, method.lower())
		params = {'headers':headers}
		if data is not None:
			params['data'] = data
		if auth is not None:
			params['auth'] = tuple(auth.split(':', 1))

		try:
			jobs = []
			pool = Pool(concurrency)
			if requests_total is not None:
				jobs = [pool.spawn(self.call, method, url, **params) for i in range(requests_total)]
				pool.join()
			else:
				with gevent.Timeout(duration, False):
					jobs = []
					while True:
						jobs.append(pool.spawn(self.call, method, url, **params))
						pool.join()

		except KeyboardInterrupt:
			pass

		ret['total_time'] = time.time() - start

	def parse_result(self):
		durations = []
		count = 0
		for i in ret['msg'].values():
			durations += i
			count += len(i)
		total_duration = sum(durations)
		total_time = ret['total_time']
		rps = 0 if count == 0 else count / total_time
		avg = total_duration / count if count > 0 else 0
		max_ = max(durations)
		min_ = min(durations)

		self.print_result(stats(count, total_time, rps, avg, min_, max_))

	def print_result(self, stats):

		print('*'*100)
		print('')
		print('-------------- Result --------------')

		print('total success calls {} '.format(stats.count))
		print('total time {} '.format(stats.total_time))
		print('average time {} ' .format(stats.avg))
		print('minimum time {} ' .format(stats.min))
		print('maximum time {} ' .format(stats.max))
		print('rps is {} ' .format(stats.rps))

		print('*'*100)
		print('-------------- Status codes --------------')
		
		for code, status in ret['msg'].items():
			print('code  {}  times  {}  '.format(code, len(status)))

		print('rps: request per second')


	def parse_args(self):
		parser = argparse.ArgumentParser(description='simple http pressure test tool')
		parser.add_argument('-m', '--method', help='Http Method', type=str, default='GET', choices=http_methods)
		parser.add_argument('--content_type', help='Content-Type', type=str, default='text/plain')
		parser.add_argument('-D', '--data', help='Data', type=str)
		parser.add_argument('-c', '--concurrency', help='Concurency', type=int, default=1)
		parser.add_argument('-a', '--auth', help='Basic Authentication user:password', type=str)
		parser.add_argument('--header', help='Custom Header key:value', type=str, action='append')

		#either total requests or total duration
		group = parser.add_mutually_exclusive_group()
		group.add_argument('-n', '--requests', help='Numbers Of Requests', type=int)
		group.add_argument('-d', '--duration', help='Duration In Seconds', type=int)

		parser.add_argument('url', help='target url', nargs='?')

		args = parser.parse_args()

		if args.url is None:
			print('please provide an URL')
			parser.print_usage()
			sys.exit(0)

		if args.requests is None and args.duration is None:
			args.requests = 1

		if args.data is not None  and args.method not in data_methods:
			print('{} method cant request with data'.format(args.method))

		def _split_header(header):
			headers = header.split(':')
			if len(headers) != 2:
				print('header should be in the format of key:value')
				parser.usage()
				sys.exit(0)
			return headers

		if args.header is not None:
			headers = dict([_split_header(header) for header in args.header])
		else:
			headers = {}

		if 'content-type' not in headers:
			headers['Content-Type'] = args.content_type

		try:
			self.run(args.url, args.requests, args.concurrency, args.duration, args.method, args.data, args.auth, headers=headers)
		except Exception as e:
			print(e)
			sys.exit(1)

		self.parse_result()

		print('Done!')



class ToolException(Exception):
	
	def __init__(self, error_msg):
		self.error_msg = error_msg

	def __str__(self):
		return self.error_msg




if __name__ == '__main__':
	obj = Tools()
	obj.parse_args()


