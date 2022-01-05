#!/usr/bin/python3
import signal
import time
from socket import *
from _thread import *
import threading
from sys import *
import os
from pam import *
from getpass import *
list_of_clients = []

#Close data connection for passive transfer
def closeData(pasv_dataSock):
	pasv_dataSock.close()

#Create passive data connection
def createData(connectionSock):
	dataSock = socket(AF_INET, SOCK_STREAM)
	dataSock.bind(('',0))
	dataSock.listen(1)
	dataPort = str(dataSock.getsockname()[1])
	connectionSock.send(dataPort.encode())
	pasv_dataSock, addr = dataSock.accept()
	#print("data connection established")
	return pasv_dataSock

#Connect to normal data socket
def connectData(data):
	data = data.split()
	clientName = data[1]
	dataPort = int(data[0])
	dataSock = socket(AF_INET, SOCK_STREAM)
	dataSock.connect((clientName,dataPort))
	#print("connected")
	return dataSock, dataPort	
anonymous = 0

#Handle ftp commands on server side
def ftp_handler(connectionSock, addr):
	pasv_flag = False
	auth_flag = 0
	global anonymous
	while (True):
		p = pam()	
		cmnd = connectionSock.recv(1024).decode()
		org_cmnd = cmnd.split()
		if(cmnd == "user"):		
			while (True):
				auth = connectionSock.recv(1024).decode()
				try:
					lst = auth.split()
					if(lst[0] == "anonymous"):
						connectionSock.send("0".encode())
						anonymous = 1
						auth_flag = 1
						break;
					if(p.authenticate(lst[0], lst[1])):
						connectionSock.send("0".encode())
						auth_flag = 1			
						break
					else:
						connectionSock.send("1".encode())
				except:
					connectionSock.send("1".encode())
			continue	
		if(auth_flag == 0):
			continue


		if(org_cmnd[0] == "cat" or org_cmnd[0] == "chmod" or org_cmnd[0] == "dir" or org_cmnd[0] == "mkdir" or org_cmnd[0] == "rmdir"):		
			if(anonymous == 0):
				if(pasv_flag == False):
					data = connectionSock.recv(1024).decode()
					data = (data + " " + addr[0])  		
					dataSock, dataPort = connectData(data)
				else:
					dataSock = createData(connectionSock)
				cmnd = cmnd + " > temp.txt"
				os.system(cmnd)
				obj = os.stat("temp.txt")
				connectionSock.send(str(obj.st_size).encode())
				with open("temp.txt", "rb") as f:
					#print("[+] sending file...")
					data = f.read()
					dataSock.sendall(data)
				f.close()
				closeData(dataSock)
				os.system("rm temp.txt")
			continue
		elif(org_cmnd[0] == "pasv"):
			
			if(pasv_flag == False):
				pasv_flag = True
			else:
				pasv_flag = False
			continue

		elif(org_cmnd[0] == "delete" or org_cmnd[0] == "mdelete"):
			if(anonymous == 0):
				if(org_cmnd[0] == "delete" ):
					cmnd = cmnd.replace("delete", "rm")
				if(org_cmnd[0] == "mdelete" ):
					cmnd = cmnd.replace("mdelete", "rm")
				
				if(pasv_flag == False):
					data = connectionSock.recv(1024).decode()
					data = (data + " " + addr[0])  		
					dataSock, dataPort = connectData(data)
				else:
					dataSock = createData(connectionSock)
				cmnd = cmnd + " > temp.txt"
				os.system(cmnd)
				obj = os.stat("temp.txt")
				connectionSock.send(str(obj.st_size).encode())
				with open("temp.txt", "rb") as f:
					#print("[+] sending file...")
					data = f.read()
					dataSock.sendall(data)
				f.close()
				closeData(dataSock)
				os.system("rm temp.txt")
			continue
		elif(org_cmnd[0] == "mdir"):
			if(anonymous == 0):
				if(pasv_flag == False):
					data = connectionSock.recv(1024).decode()
					data = (data + " " + addr[0])  		
					dataSock, dataPort = connectData(data)
				else:
					dataSock = createData(connectionSock)
				path = os.getcwd()
				l = len(org_cmnd) - 1;
				i = 1;
				strn = "\n"
				while(i <= l):
					temppath = path +  "/" + org_cmnd[i];
					str1 = "150 Here comes the directory listing for " + org_cmnd[i] + "-"
					lst1 = os.listdir(temppath)
					for x in lst1:
						str1 = str1 +"\t"+  x
					str1 = str1 + '\n'
					strn = strn + str1
					i += 1
				length = len(strn) + 1
				connectionSock.send(str(length).encode())
				dataSock.send(strn.encode()) 
					
				closeData(dataSock)
			continue
		elif(org_cmnd[0] == "ls"):
			if(pasv_flag == False):
				data = connectionSock.recv(1024).decode()
				data = (data + " " + addr[0])  		
				dataSock, dataPort = connectData(data)
			else:
				dataSock = createData(connectionSock)
			path = os.getcwd()
			lst1 = os.listdir(path)
			str1 = "150 Here comes the directory listing.\n"
			for x in lst1:
				str1 = str1 +"\t"+  x
			length = len(str1) + 1
			connectionSock.send(str(length).encode())
			dataSock.send(str1.encode())
			closeData(dataSock)
			
		elif(org_cmnd[0] == "pwd"):
			if(pasv_flag == False):
				data = connectionSock.recv(1024).decode()
				data = (data + " " + addr[0])  		
				dataSock, dataPort = connectData(data)
			else:
				dataSock = createData(connectionSock)
			path = os.getcwd()
			connectionSock.send(str(len(path)).encode())
			dataSock.send(path.encode())
			closeData(dataSock)
					
	
		elif(org_cmnd[0] == "cd"):
			try:
				os.chdir(org_cmnd[1])
				response = "250 Directory successfuly changed."
			except:
				response = "Command Failed"
			finally:
				if(pasv_flag == False):
					data = connectionSock.recv(1024).decode()
					data = (data + " " + addr[0])  		
					dataSock, dataPort = connectData(data)
				else:
					dataSock = createData(connectionSock)
				connectionSock.send(str(len(response)).encode())
				dataSock.send(response.encode())
				closeData(dataSock)
			continue
		elif(org_cmnd[0] == "reget"):
			size = 0
			if(pasv_flag == False):
				data = connectionSock.recv(1024).decode()
				data = (data + " " + addr[0])  		
				dataSock, dataPort = connectData(data)
			else:
				dataSock = createData(connectionSock)
			size = int(connectionSock.recv(1024).decode())
			try:
				obj = os.stat(org_cmnd[1])
			except:
				connectionSock.send("0".encode())
				continue
			path = os.getcwd() + "/" + org_cmnd[1]			
			if(os.path.isdir(path)):
				connectionSock.send("0".encode())
				continue
			newsize = obj.st_size - size - 1
			connectionSock.send(str(newsize).encode())
			f = open(org_cmnd[1], "rb")
			f.seek(size)
			data = f.read()				
			dataSock.sendall(data)
			f.close()
			closeData(dataSock)
			continue
		elif(org_cmnd[0] == "get"):
			if(pasv_flag == False):
				data = connectionSock.recv(1024).decode()
				data = (data + " " + addr[0])  		
				dataSock, dataPort = connectData(data)
			else:
				dataSock = createData(connectionSock)
			try:
				obj = os.stat(org_cmnd[1])
			except:
				connectionSock.send("0".encode())
				continue
			path = os.getcwd() + "/" + org_cmnd[1]
			if(os.path.isdir(path)):
				connectionSock.send("0".encode())
				continue
			connectionSock.send(str(obj.st_size).encode())
			with open(org_cmnd[1], "rb") as f:
				#print("[+] sending file...")
				data = f.read()
				dataSock.sendall(data)
			f.close()
			closeData(dataSock)
			continue
		elif(org_cmnd[0] == "mget"):
			length = len(org_cmnd) - 1
			i = 1
			while(length):
				length -= 1
				if(pasv_flag == False):
					data = connectionSock.recv(1024).decode()
					data = (data + " " + addr[0])  		
					dataSock, dataPort = connectData(data)
				else:
					dataSock = createData(connectionSock)
				try:
					obj = os.stat(org_cmnd[i])
				except:
					connectionSock.send("0".encode())
					i += 1
					continue
				path = os.getcwd() + "/" + org_cmnd[1]
				if(os.path.isdir(path)):
					connectionSock.send("0".encode())
					continue
				connectionSock.send(str(obj.st_size).encode())
				with open(org_cmnd[i], "rb") as f:
					#print("[+] sending file...")
					data = f.read()
					dataSock.sendall(data)
				f.close()
				closeData(dataSock)
				i += 1
				
			continue
		elif(org_cmnd[0] == "put"):
			if(anonymous == 0):
				if(pasv_flag == False):
					data = connectionSock.recv(1024).decode()
					data = (data + " " + addr[0])  		
					dataSock, dataPort = connectData(data)
				else:
					dataSock = createData(connectionSock)			
				size = int(connectionSock.recv(1024).decode())
				if(size):
					f = open(org_cmnd[1], "ab")
					while (size > 0):
						data = dataSock.recv(1024)				
						f.write(data)
						size -= 1024
					f.close()
				closeData(dataSock)
			continue
		elif(org_cmnd[0] == "mput"):
			if(anonymous == 0):
				length = len(org_cmnd) - 1
				i = 1
				while(length):
					if(pasv_flag == False):
						data = connectionSock.recv(1024).decode()
						data = (data + " " + addr[0])  		
						dataSock, dataPort = connectData(data)
					else:
						dataSock = createData(connectionSock)	
					size = int(connectionSock.recv(1024).decode())
					if(size):
						f = open(org_cmnd[i], "ab")	
						while (size > 0):
							data = dataSock.recv(1024)				
							f.write(data)
							size -= 1024
						f.close()
					closeData(dataSock)
					i += 1
					length -= 1
			continue
				
		elif(org_cmnd[0] == "quit" or org_cmnd[0] == "bye" or org_cmnd[0] == "exit" or org_cmnd[0] == "disconnect"):
			list_of_clients.remove(connectionSock)
			connectionSock.close()
			break
		
		else:
			continue		

#For control c disable
def handler(signum, frame):
	pass

def Main():
	if(len(argv) < 2):
		print("Insufficient Arguments : usage : ./ftpser.py Port_Number")
		exit(1)
	controlPort = int(argv[1])
	controlSock = socket(AF_INET, SOCK_STREAM)
	try:	
		controlSock.bind(('',controlPort))
	except:
		print("Bind failed")
		exit(1)
	try:	
		controlSock.listen(50)
	except:
		print("listen failed")
		exit(1)
	#print('Control connection established')
	global list_of_clients

	#Timeout function for server
	controlSock.settimeout(30000.0)
	
	#To disable control c
	signal.signal(signal.SIGINT, handler)
	while True:
		try:
			connectionSock, addr = controlSock.accept()
		except:
			if(len(list_of_clients) == 0):
				controlSock.close()
				exit(0)
			else:
				continue
		list_of_clients.append(connectionSock)
		start_new_thread(ftp_handler, (connectionSock, addr,))

		
	controlSock.close()	
	return 0

if __name__ == '__main__':
	Main()
