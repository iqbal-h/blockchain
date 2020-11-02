import multiprocessing
import threading 
import sys
import os
from time import sleep, time
import time
import signal
import subprocess
from datetime import datetime
import socket
from collections import OrderedDict

import binascii
import Crypto
import Crypto.Random
from Crypto.Hash import SHA
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
import random
import hashlib
import json


try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
    
# from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

from blockchain import *

# usleep = lambda x: time.sleep(x/1000000.0)

node_address_d = {}
private_keys_d = {}
public_keys_d  = {}


pre_prepare = {}
prepare     = {}
commit      = {}
reply       = {}


total_nodes = 0
TOTALTRASPOST = 100
TOTALTRASFETCH = 100
PORTFACTOR = 5000

current_time_us = lambda: int(round(time() * 1000000))

MINE_MINT = -1
total_nodes = 0
IOT1 = 0
IOT2 = 0	
log_suffix = ""

commit_counter = 0


def signal_handler(sig, frame):

	print('You pressed Ctrl+C! MPP Exit.')
	sys.exit(0)


def blockchain_node(pid,total_nodes, node_address_d, lock):
	global commit_counter
	# global lock
	# global node_address_d
	if pid == 0:
		fh = open('keys', 'w')
	else:
		fh = open('addresses', 'a')

	ret = new_wallet()

	private_key = ret['private_key']
	public_key  = ret['public_key']

	private_keys_d[pid] = private_key
	public_keys_d[pid]  = public_key

	node = Blockchain()
	uuid = node.node_id
	node_address_d[pid] = uuid
	
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	# Bind the socket to the port
	server_address = ('localhost', PORTFACTOR+pid)
	print ('Starting up node on <port,pid,UUID>:', (PORTFACTOR+pid), pid, str(uuid))
	sock.bind(server_address)

	
	count = 0

	pbft_d = {}
	ct_count = 0
	desired_count = int(total_nodes/3)
	first_value = ""

	while True:

		# print (pid, "recv")
		data, address = sock.recvfrom(4096)
		data = data.decode().split(">")
		# print (data)
		flag = data[0]
		
		# New transaction
		if flag == "FT":
			# print (pid, "FETCH")
			t_value    = data[1]
			t_value_in = t_value+"~"
			match_found = 'N'
			# for i in range(0, len(node.chain)):
			i = len(node.chain) - 1
			while i >= 0:
				trans = node.chain[i]['transactions']
				if len(trans) > 0:
					for d in trans:
						if d['value'] == t_value:
							match_found = 'V'
							
						elif d['value'] == t_value_in:
							match_found = 'R'
					if match_found != 'N':
						break
				i -= 1
						# print ("BLOCK: ", i, d['value'])
			data = str(current_time_us())+','+str(match_found)+','+data[1]
			# print ("SENDING FT RESP: ", data)
			sent = sock.sendto(data.encode(), address)

		elif flag == 'FA': # Fetch all Transaction
			all_trans = ""
			print (pid, len(node.chain))
			for i in range(0, len(node.chain)):
				trans = node.chain[i]['transactions']
				if len(trans) > 0:
					for d in trans:
						all_trans += str(d)+"\n"
						print ("BLOCK: ", pid, i, d)

			fh = open("./logs/all_transactions_"+str(pid), "w")
			fh.write(all_trans)
			all_trans = ""
			fh.close()

		elif flag == 'NT': # New transaction
			msg  = json.loads(data[1])
			# print ('received %s bytes from %s' % (len(data), address))
			# print (flag, msg )
			count += 1
			ret = new_transaction(node, msg)
			# print (pid, ret)

		elif flag == 'PP': # PBFT Pre-prepare
			# print (pid, 'PP', data)
			message = 'PR>'+str(data[1])+'>'+data[2]+'>'+data[3]
			pbft_prepare(sock, total_nodes, pid, message, PORTFACTOR)


		elif flag == 'PR': # PBFT Prepare
			# print (pid, 'PR')
			message = 'CT>'+str(data[1])+'>'+data[2]+'>'+data[3]
			pbft_commit(sock, total_nodes, pid, message, PORTFACTOR)

		elif flag == 'CT': # PBFT Commit
			# print (pid, 'CT')
			# ct_count += 1
			if data[2] != first_value:
				pbft_d[address] = data[2]


			if len(pbft_d) >= desired_count:
				keys = list(pbft_d.keys())
				first_value = pbft_d[keys[0]]
				ct_count += 1

				for i in range(1, len(pbft_d)):
					if pbft_d[keys[i]] == first_value:
						ct_count += 1

				if ct_count >= desired_count:
					if pid != int(data[1]):
						block = json.loads(data[3])
						node.chain.append(block)

						# lock.acquire()
						# commit_counter += 1
						# lock.release()
						# sleep(0.00001)
						# commit_counter += 1

					pbft_d = {}
			
		    
		if count > 0:
			if MINE_MINT == 0:
				ret = mine(node)
				count = 0
				# print ("MINE: ", ret)
				# print ("MINE: ",pid)

			elif MINE_MINT == 1:
				ret = mint(node, total_nodes, pid, sock, PORTFACTOR)
				count = 0
				# print ("MINT: ", pid)


def test_transaction_generator_all_nodes(sock, value):


	# serv_port = random.randint(0,total_nodes+100) % total_nodes
	server_address = ('localhost', PORTFACTOR+0)
	# message = 'This is the message.  It will be repeated.'
	# print (len(private_keys_d), len(public_keys_d))

	# value = 'A-B'	
	gen_trans = generate_transaction(node_address_d[0], private_keys_d[0], node_address_d[1], value)
	
	
	x = json.dumps(gen_trans)
	message = 'NT'+">"+x
	try:
	    print ('sending trans to "%s"' % str(server_address))
	    sent = sock.sendto(message.encode(), server_address)

	except Exception as EE:
		print ("Exeception transaction_generator_all_nodes: ", EE)




def transaction_set_generator(sock, node_id):

	total_trans = 0
	trans_log = ""
	iot_1 = 1
	iot_2 = 1
	revoke = 0

	serv_port = PORTFACTOR+node_id+1
	
	server_address = ('localhost', serv_port)
	
	
	while iot_1 < IOT1:
		print ("transaction_set_generator:", iot_1)
		for i in range(1, IOT2):
			iot_2 = i
			if iot_1 != i:
				value = str(iot_1)+"-"+str(iot_2)
				gen_trans = generate_transaction(node_address_d[node_id], private_keys_d[node_id], node_address_d[node_id+1], value)
				val = str(current_time_us())+","+ str(serv_port)+","+str(server_address) + "," + value + "\n"
				trans_log += val
				
				x = json.dumps(gen_trans)
				message = 'NT'+">"+x
				try:
				    sent = sock.sendto(message.encode(), server_address)
				except Exception as EE:
					print ("Exeception transaction_generator_all_nodes: ", EE)
	
			# sleep(0.001)
		iot_1 += 1

	fh = open("./logs/transaction_set_generator_LOG_"+log_suffix, "w")
	fh.write(trans_log)
	fh.close()


def transaction_set_revoker_and_get_delayed(sock, node_id, lock):
	# global lock
	global commit_counter
	total_trans = 0
	trans_log = ""
	get_log   = ""
	iot_1 = 1
	iot_2 = 1
	revoke = 0
	
	lock.acquire()
	try:
		commit_counter = 0
	finally:
	    lock.release()

	print ("ST:", commit_counter)
	fh_1 = open("./logs/transaction_set_revoker_and_get_delayed_GETRESP_LOG_"+log_suffix, "w")

	while iot_1 < IOT1:
		print ("REV:", iot_1)
		for i in range(1, IOT2):
			iot_2 = i
			if iot_1 != i:
				value = str(iot_1)+"-"+str(iot_2)+'~'
				gen_trans = generate_transaction(node_address_d[node_id], private_keys_d[node_id], node_address_d[node_id+1], value)
				
				# REVOKE TRANSACTION				
				x = json.dumps(gen_trans)
				message = 'NT'+">"+x
				try:
					serv_port = PORTFACTOR+node_id+1
					server_address = ('localhost', serv_port)
					sent = sock.sendto(message.encode(), server_address)
					val = "REV,"+str(current_time_us())+","+ str(serv_port)+","+str(server_address) + "," + value
					trans_log += val+"\n"
				except Exception as EE:
					print ("Exeception transaction_set_revoker_and_get_delayed: ", EE)

				# delay = float(random.randint(1,20))/1000.0 #10
				delay = float(random.randint(1,50))/1000.0 #10
				# delay = float(random.randint(17,100))/1000.0 # 15
				# print (delay)
				sleep(delay)
				temp_ts = current_time_us()		

				


				y = 0

				# serv_port = PORTFACTOR+2
				# serv_port = PORTFACTOR+int(total_nodes/2)+1
				serv_port = PORTFACTOR+int(total_nodes)-1


				# while commit_counter < 2:
				# while commit_counter < int(total_nodes/2)+1:
				while commit_counter < int(total_nodes)-1:
				# while commit_counter < 3:
					# lock.acquire()
					# try:
					# 	if commit_counter < int(total_nodes)-1:
					# 		y = -10
					# finally:
					#     lock.release()

					# lock.acquire()
					# # if commit_counter >= 1:
					# if commit_counter >= int(total_nodes/2)+1:
					# # if commit_counter >= int(total_nodes)-1:
					# 	y = -10
					# lock.release()
					# sleep(0.015)
					# y = 1
					sleep(0.019)
					y += 1
					if  y > 200 or y < 0:  # 20000000 = 1sec; 10000000 = 0.5sec  //y > 20000000 or
						break

				lock.acquire()
				print (commit_counter)
				commit_counter = 0
				lock.release()
					


				

				# GET
				value = str(iot_1)+"-"+str(iot_2)
				message = "FT"+">"+str(value)

				try:
					
					server_address = ('localhost', serv_port)
					sent = sock.sendto(message.encode(), server_address)
					val += ",FT,"+str(temp_ts)+","+ str(serv_port)+","+str(server_address) + "," + value
					# get_log += val

					data, address = sock.recvfrom(4096)
					data = data.decode()
					val += ",RESP,"+str(data) + "," + str(address) + "\n"
					# print (rep)
					fh_1.write(val)
					# get_log += val
				except Exception as EE:
					print ("Exeception transaction_set_revoker_and_get_delayed: ", EE)

				sleep(0.05)


	
			# sleep(0.001)
		iot_1 += 1

	fh_1.close()

	fh = open("./logs/transaction_set_revoker_and_get_delayed_REVOKE_LOG_"+log_suffix, "w")
	fh.write(trans_log)
	fh.close()

	
	
	

def transaction_set_revoker_and_get(sock, node_id):

	total_trans = 0
	trans_log = ""
	get_log   = ""
	iot_1 = 1
	iot_2 = 1
	revoke = 0
		
	while iot_1 < IOT1:
		print ("transaction_set_revoker_and_get:", iot_1)
		for i in range(1, IOT2):

			iot_2 = i
			if iot_1 != i:
				value = str(iot_1)+"-"+str(iot_2)+'~'
				gen_trans = generate_transaction(node_address_d[node_id], private_keys_d[node_id], node_address_d[node_id+1], value)
				
				# REVOKE TRANSACTION				
				x = json.dumps(gen_trans)
				message = 'NT'+">"+x
				try:
					serv_port = PORTFACTOR+node_id
					# serv_port = PORTFACTOR+1
					server_address = ('localhost', serv_port)
					sent = sock.sendto(message.encode(), server_address)
					val = "REV,"+str(current_time_us())+","+ str(serv_port)+","+str(server_address) + "," + value
					trans_log += val+"\n"
				except Exception as EE:
					print ("Exeception transaction_set_revoker_and_get: ", EE)


				# GET
				value = str(iot_1)+"-"+str(iot_2)
				message = "FT"+">"+str(value)
				try:
					# serv_port = PORTFACTOR+int(total_nodes/2)+1
					serv_port = PORTFACTOR+1
					server_address = ('localhost', serv_port)
					sent = sock.sendto(message.encode(), server_address)
					val += ",FT,"+str(current_time_us())+","+ str(serv_port)+","+str(server_address) + "," + value
					# get_log += val

					data, address = sock.recvfrom(4096)
					data = data.decode()
					val += ",RESP,"+str(data) + "," + str(address) + "\n"
					# print (rep)
					get_log += val
				except Exception as EE:
					print ("Exeception get_persmission_value: ", EE)
	
			# sleep(0.001)
		iot_1 += 1

	fh = open("./logs/transaction_set_revoker_and_get_REVOKE_LOG_"+log_suffix, "w")
	fh.write(trans_log)
	fh.close()

	fh = open("./logs/transaction_set_revoker_and_get_GETRESP_LOG_"+log_suffix, "w")
	fh.write(get_log)
	fh.close()

# To be ran in multi threading
def transaction_set_revoker(sock, node_id):

	total_trans = 0
	trans_log = ""
	iot_1 = 1
	iot_2 = 1
	revoke = 0

	serv_port = PORTFACTOR+node_id+1
	
	server_address = ('localhost', serv_port)
		
	while iot_1 < IOT1:
		# print ("REV:", iot_1)
		for i in range(1, IOT2):
			iot_2 = i
			if iot_1 != i:
				value = str(iot_1)+"-"+str(iot_2)+'~'
				gen_trans = generate_transaction(node_address_d[node_id], private_keys_d[node_id], node_address_d[node_id+1], value)
				
				# REVOKE
				x = json.dumps(gen_trans)
				message = 'NT'+">"+x
				try:
					sent = sock.sendto(message.encode(), server_address)
					val = str(current_time_us())+","+ str(serv_port)+","+str(server_address) + "," + value + "\n"
					trans_log += val
				except Exception as EE:
					print ("Exeception transaction_set_revoker: ", EE)


				
	
			# sleep(0.001)
		iot_1 += 1

	fh = open("./logs/transaction_set_revoker_LOG_"+log_suffix, "w")
	fh.write(trans_log)
	fh.close()

def get_persmission_value(sock, node_id):

	total_trans = 0
	trans_log = ""
	resp_log = ""
	iot_1 = 1
	iot_2 = 1
	revoke = 0

	serv_port = PORTFACTOR+node_id+1
	
	server_address = ('localhost', serv_port)
		
	while iot_1 < IOT1:
		# print ("GET:", iot_1)
		for i in range(1, IOT2):
			iot_2 = i
			if iot_1 != i:
				value = str(iot_1)+"-"+str(iot_2)
				val = str(current_time_us())+","+ str(serv_port)+","+str(server_address) + "," + value + "\n"
				trans_log += val
				
				# x = json.dumps(value)
				message = "FT"+">"+str(value)
				try:
				    sent = sock.sendto(message.encode(), server_address)
				    data, address = sock.recvfrom(4096)
				    data = data.decode()
				    rep = str(data) + "," + str(address) + "\n"
				    # print (rep)
				    resp_log += rep
				except Exception as EE:
					print ("Exeception get_persmission_value: ", EE)
	
			sleep(0.001)
		iot_1 += 1

	fh = open("./logs/get_persmission_value_LOG_"+log_suffix, "w")
	fh.write(trans_log)
	fh.close()

	fh = open("./logs/get_persmission_value_response_LOG_"+log_suffix, "w")
	fh.write(resp_log)
	fh.close()

def transaction_generator_all_nodes(sock):

	total_trans = 0
	trans_log = ""
	iot_1 = 1
	iot_2 = 2
	revoke = 0
	while total_trans < TOTALTRASPOST:

		serv_port = random.randint(0,total_nodes+100) % total_nodes
		server_address = ('localhost', PORTFACTOR+serv_port)
		# message = 'This is the message.  It will be repeated.'

		# print (len(private_keys_d), len(public_keys_d))


		if (revoke % 10) == 0:
			value = str(int(iot_1/2))+"-"+str(int(iot_2/3))+"~"
		else:
			value = str(iot_1)+"-"+str(iot_2)
		iot_1 += 1
		iot_2 += 1

		revoke += 1		
		
		gen_trans = generate_transaction(node_address_d[0], private_keys_d[0], node_address_d[1], value)
		val = str(current_time_us())+","+str(serv_port) + "," + value + "\n"
		trans_log += val
		x = json.dumps(gen_trans)
		message = 'NT'+">"+x
		try:
		    # print ('sending trans to "%s"' % str(server_address))
		    sent = sock.sendto(message.encode(), server_address)

		except Exception as EE:
			print ("Exeception transaction_generator_all_nodes: ", EE)

		total_trans += 1
		sleep(0.1)

	fh = open("./logs/trans_logs", "w")
	fh.write(trans_log)
	fh.close()



def transaction_fetcher(sock):

	total_trans = 0
	trans_log = ""
	iot_1 = 1
	iot_2 = 2
	revoke = 0

	print ("\n\n transaction_fetcher\n\n")
	while total_trans < TOTALTRASFETCH:

		serv_port = random.randint(0,total_nodes+100) % total_nodes
		server_address = ('localhost', PORTFACTOR+serv_port)

		iot_1 = random.randint(0,100)
		iot_2 = random.randint(0,100)

		if iot_1 == iot_2:
			iot_2 += 1

		if revoke % 5 == 0:
			message = 'FT>' + str(iot_1) + '-' + str(iot_2) + '~'
		else:
			message = 'FT>' + str(iot_1) + '-' + str(iot_2)

		print ('FT :', str(server_address), message)
		
		try:
			tstamp = str(current_time_us())
			sent = sock.sendto(message.encode(), server_address)

			data, server = sock.recvfrom(4096)
			data = data.decode()

			print ("RET:", data)

			val = tstamp + "," + str(serv_port) + "," + message + "," + str(data) + "\n"
			trans_log += val


		except Exception as tf:
			print("Exception transaction_fetcher: ". tf)


		total_trans += 1
		revoke += 1
		sleep(0.2)

	fh = open("./logs/transaction_fetch_logs", "w")
	fh.write(trans_log)
	fh.close()





if __name__ == "__main__": 


	signal.signal(signal.SIGINT, signal_handler)
	args = sys.argv[1:]
	argc = len(args)


	if argc != 6:
		print ("Usage Issue. Need 6 Argument.")
		print ("python3.7 executer.py <no of nodes> <PoV or PoA> <Port Factor> <IoT_1> <IoT_2> <suffics>")
		exit(1)

	process_list = []
	total_nodes  = int(args[0])
	MINE_MINT 	 = int(args[1]) 	# 0 MINE 1 MINT
	PORTFACTOR   = int(args[2])
	IOT1     	 = int(args[3])
	IOT2     	 = int(args[4])
	suffics      = args[5]


	# t = time()
	# y = 0
	# while True:

	# 	y += 1
	# 	if y > 10000000:
	# 		break

	# print ("TIME: ", time() - t)
	# exit(1)

	print ("Number of Nodes = ", total_nodes)

	if MINE_MINT == 0:
		print ("Consensus Algorithm : Proof of Work using Mining")
	elif MINE_MINT == 1:
		print ("Consensus Algorithm : PBFT")
	else:
		print ("Please provide Consensus Algorithm : 0 = Mining, 1 = PBFT")
		exit(1)

	log_suffix = str(total_nodes)+"_"+str(MINE_MINT)+"_"+str(IOT1)+"_"+str(IOT2)+"_"+suffics


	for i in range(0, total_nodes):
		node_address_d[i] = ""

	lock = threading.Lock()
	# try:
	print (node_address_d)
	for i in range(0, total_nodes):
		# p = multiprocessing.Process(target=busy_hour, args=(i, source_list[i], dest_path, prefix_list[i]))
		p = threading.Thread(target=blockchain_node, args=(i, total_nodes, node_address_d, lock))
		process_list.append(p)
		p.start()
		sleep(0.3)

	sleep(1)
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	# test_transaction_generator_all_nodes(sock, 'A-B')
	# test_transaction_generator_all_nodes(sock, 'A-C')



	# transaction_set_generator(sock, 0)
	# print ("IOT PERMISSION SET ADDED")
	# sleep(1)
	# tr = threading.Thread(target=transaction_set_revoker, args=(sock,0))
	# gt = threading.Thread(target=get_persmission_value, args=(sock,0))
	# gt.start()
	# tr.start()
	# print ("STARTING REVOKE AND GET THREADS")
	# tr.join()
	# gt.join()
	# print ("REVOKE AND GET THREADS COMPLETE")

	print ("ADDING IOT DEVICE PERMISSIONS")
	transaction_set_generator(sock, 0)
	print ("IOT PERMISSION SET ADDED")
	sleep(1)

	# print ("Starting transaction_set_revoker_and_get")
	# t = threading.Thread(target=transaction_set_revoker_and_get, args=(sock,0))
	# t.start()
	# t.join()
	# print ("End transaction_set_revoker_and_get")



	print ("Starting transaction_set_revoker_and_get_delayed")
	t = threading.Thread(target=transaction_set_revoker_and_get_delayed, args=(sock,0, lock))	
	t.start()
	t.join()
	print ("End transaction_set_revoker_and_get_delayed")



	# # add transactions and fetch in parallel
	# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	# p = threading.Thread(target=transaction_generator_all_nodes, args=(sock,))
	# process_list.append(p)
	# p.start()

	# t = threading.Thread(target=transaction_fetcher, args=(sock,))
	# process_list.append(t)
	# t.start()


	# p.join()
	# t.join()


	# print ("FETCHING ALL")
	# sleep(1)

	# for i in range(0, total_nodes):
	# 	server_address = ('localhost', PORTFACTOR+i)	
	# 	message = "FA>all"
	# 	try:
	# 	    print ('sending "%s"' % message)
	# 	    sent = sock.sendto(message.encode(), server_address)
	# 	except Exception as E:
	# 		print ("Exception in FA:", E)
	# 	sleep(0.5)



	for p in process_list:
		p.join()

