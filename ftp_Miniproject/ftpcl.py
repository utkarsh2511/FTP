#!/usr/bin/python3
import signal
from readline import *
from socket import *
from sys import *
import os 
from sys import *
from pam import *
from getpass import *
from time import *
rate = 1024
pasv_flag = False

#List of commands
cmnd_list = ["!", "?", "cd", "pwd", "ls", "get", "mget", "put", "mput", "quit", "bye", "cat", "hash", "chmod","rm", "dir", "mkdir", "help", "delete", "mdelete", "rmdir", "user", "reget", "lcd", "history", "pasv", "exit", "disconnect"]

hash_flag = False

#Establishes passive data connection
def connectData(data):
	data = data.split()
	clientName = data[1]
	pasv_dataPort = int(data[0])
	pasv_dataSock = socket(AF_INET, SOCK_STREAM)
	pasv_dataSock.connect((clientName,pasv_dataPort))
	print("passively connected")
	return pasv_dataSock, pasv_dataPort

#Closes data connection
def closeData(connectionSock):
	connectionSock.close()

#Establishes normal data connection
def createData(controlSock):
	dataSock = socket(AF_INET, SOCK_STREAM)
	dataSock.bind(('',0))
	dataSock.listen(1)
	dataPort = str(dataSock.getsockname()[1])
	controlSock.send(dataPort.encode())
	connectionSock, addr = dataSock.accept()
	print("200 PORT command successful. Consider using PASV.")
	return connectionSock

#Stores history of commands
command_history = []

#For anonymous access
anonymous = 0


class AlarmException(Exception):
	pass

def alarmHandler(signum, frame):
	raise AlarmException

def handler(signum, frame):
	pass

#To timeout when idle for 5 min 
def nonBlockingInput(prompt, timeout, controlSock):
	signal.signal(signal.SIGALRM, alarmHandler)
	signal.alarm(timeout)
	try:
		text = input(prompt)
		signal.alarm(0)
		return text
	except AlarmException:
		cmnd = "bye"
		controlSock.send(cmnd.encode())
		controlSock.close()
		print("221 Goodbye.")
		exit(0)
	signal.signal(signal.SIGALRM, signal.SIG_IGN)
	return ''


def Main():
	global hash_flag	
	global command_history	
	global pasv_flag
	global anonymous
	global rate
	if(len(argv) < 3):
		print("Insufficient Arguments usage : ./ftpcl.py IP Port_Number")
		exit(1)
	serverName = argv[1]
	serverPort = int(argv[2])
	controlSock = socket(AF_INET, SOCK_STREAM)
	try:
		controlSock.connect((serverName,serverPort))
	except:
		print("connect failed")
		exit(1)
	auth_flag = 0;
	print("connected")
	signal.signal(signal.SIGINT, handler)
	while (True):
		cmnd = nonBlockingInput("$ftp> ", 300, controlSock)
		command_history.append(cmnd)
		if(cmnd == ""):
			continue
		cmnd = cmnd.lower()
		org_cmnd = cmnd.split()
		path = ""

		#quit, bye command
		if(org_cmnd[0] == "quit" or org_cmnd[0] == "bye" or org_cmnd[0] == "exit" or org_cmnd[0] == "disconnect"):
			controlSock.send(cmnd.encode())
			controlSock.close()
			print("221 Goodbye.")
			exit(0)

		#To run local commands(using !)
		if(org_cmnd[0][0] == "!"):
			cmnd = cmnd.replace("!", '')
			cmd1 = cmnd.split()
			if(cmd1[0] == "cd"):
				try:
					os.chdir(cmd1[1])
					print("Directory changed successfuly")
				except:
					print("Failed to change the directory")

				continue
			os.system(cmnd)
			continue
		
		controlSock.send(cmnd.encode())

		#Authorization using user command 
		if(cmnd == "user"):
			while (True):
				name = input("Username: ")
				if(name == "anonymous"):
					anonymous = 1
				print("331 Password required for student.")
				password = getpass()
				string = name + " " + password
				controlSock.send(string.encode())
				auth = controlSock.recv(1024).decode()
				if(auth == "1"):
					print("530 Login incorrect.\nLogin failed.")
				else:
					auth_flag = 1
					print("230 Login successful.\nRemote system type is UNIX.\nUsing binary mode to transfer files.")
					break
			continue
		if(auth_flag == 0):
			print("530 Please login with USER and PASS.")
			continue

		#system command implementation
		if(org_cmnd[0] == "cat" or org_cmnd[0] == "chmod" or org_cmnd[0] == "dir" or org_cmnd[0] == "mkdir" or org_cmnd[0] == "rmdir"):
			
			if(anonymous == 0):
				if(pasv_flag == False):
					connectionSock = createData(controlSock)
				else:
					data = controlSock.recv(1024).decode()
					data = (data + " " + serverName)  		
					connectionSock, dataPort = connectData(data)

				f = open("1.txt", "ab")			
				size = int(controlSock.recv(1024).decode())
				while (size):
					data = connectionSock.recv(1)				
					f.write(data)
					size -= 1
				f.close()
				os.system("cat 1.txt")
				os.system("rm 1.txt")
				closeData(connectionSock)
			continue
		
		#lcd command implementation
		elif(org_cmnd[0] == "lcd"):
			try:
				os.chdir(org_cmnd[1])
				print("Directory changed successfuly")
			except:
				print("Failed to change the directory")

			continue

		#Stores history  of commands
		elif(org_cmnd[0] == "history"):
			for x in command_history:
				print (x)
				print('\n')
			continue

		#To toggle between passive and normal mode
		elif(org_cmnd[0] == "pasv"):
			if(pasv_flag == False):
				pasv_flag = True
				print("Entering passive mode")
			else:
				pasv_flag = False
				print("Entering normal mode" )

		#Multiple directory listing command implementation
		elif(org_cmnd[0] == "mdir"):
			if(pasv_flag == False):
				connectionSock = createData(controlSock)
			else:
				data = controlSock.recv(1024).decode()
				data = (data + " " + serverName)  		
				connectionSock, dataPort = connectData(data)
			l = len(org_cmnd) - 1
			length = int(controlSock.recv(1024).decode())
			print(connectionSock.recv(length).decode())
			closeData(connectionSock)
			print("226 Directory send OK.")				
			continue
		
		#delete and mdelete command implementation
		elif(org_cmnd[0] == "delete" or org_cmnd[0] == "mdelete"):
			if(anonymous == 0):
				org_cmnd[0] = "rm"
				
				if(pasv_flag == False):
					connectionSock = createData(controlSock)
				else:
					data = controlSock.recv(1024).decode()
					data = (data + " " + serverName)  		
					connectionSock, dataPort = connectData(data)

				f = open("1.txt", "ab")			
				size = int(controlSock.recv(1024).decode())
				while (size):
					data = connectionSock.recv(1)				
					f.write(data)
					size -= 1
				f.close()
				os.system("cat 1.txt")
				os.system("rm 1.txt")
				closeData(connectionSock)
			continue
		#To display list of commands
		elif(org_cmnd[0] == "help" or org_cmnd[0] == "?"):
			for i in range(0, len(cmnd_list)):
				print(cmnd_list[i], end = "\t\t")
				if((i + 1 )% 4 == 0):
					print("\n")
			print("")
			continue
		
		#ls command implementation
		elif(org_cmnd[0] == "ls"):
			
			if(pasv_flag == False):
				connectionSock = createData(controlSock)
			else:
				data = controlSock.recv(1024).decode()
				data = (data + " " + serverName)  		
				connectionSock, dataPort = connectData(data)

			length = int(controlSock.recv(1024).decode())
			print(connectionSock.recv(length).decode())
			
			closeData(connectionSock)
			print("226 Directory send OK.")				
			continue

		#pwd command implementation
		elif(org_cmnd[0] == "pwd"):
			
			if(pasv_flag == False):
				connectionSock = createData(controlSock)
			else:
				data = controlSock.recv(1024).decode()
				data = (data + " " + serverName)  		
				connectionSock, dataPort = connectData(data)

			length = int(controlSock.recv(1024).decode())
			print('257 "{}" is the current directory'.format(connectionSock.recv(length).decode()))
			closeData(connectionSock)
			continue

		#cd command implementation
		elif(org_cmnd[0] == "cd"):
			
			if(pasv_flag == False):
				connectionSock = createData(controlSock)
			else:
				data = controlSock.recv(1024).decode()
				data = (data + " " + serverName)  		
				connectionSock, dataPort = connectData(data)

			length = int(controlSock.recv(1024).decode())
			response = connectionSock.recv(length).decode()
			print(response)	
			closeData(connectionSock)
			continue

		#To get file from server
		elif(org_cmnd[0] == "get"):
			t_start = time()		
			
			if(pasv_flag == False):
				connectionSock = createData(controlSock)
			else:
				data = controlSock.recv(1024).decode()
				data = (data + " " + serverName)  		
				connectionSock, dataPort = connectData(data)
				
			size = int(controlSock.recv(1024).decode())
			d_size = size
			if(size > 0):
				f = open(org_cmnd[1], "ab")
				while (size > 0):
					data = connectionSock.recv(rate)				
					f.write(data)
					if(hash_flag):
						print("#", end = "")
					size -= rate
					
				f.close()
				print("\n", end = "")
			closeData(connectionSock)
			t_end = time()
			net_time = t_end - t_start
			if(d_size != 0):
				print("{} bytes received in {} seconds".format(d_size, net_time))
			else:
				print("Bad file name")
			continue
		
		#To complete transfer of partially transfered files		
		elif(org_cmnd[0] == "reget"):
			t_start = time()
			newsize = size = 0
			if(pasv_flag == False):
				connectionSock = createData(controlSock)
			else:
				data = controlSock.recv(1024).decode()
				data = (data + " " + serverName)  		
				connectionSock, dataPort = connectData(data)			
			try:
				obj = os.stat(org_cmnd[1])
				size = obj.st_size
			except:
				size = 0
			controlSock.send(str(size).encode())
			newsize = int(controlSock.recv(1024).decode())
			d_size = newsize
			if(newsize > 0):
				f = open(org_cmnd[1], "ab")
				while (newsize > 0):
					data = connectionSock.recv(rate)				
					f.write(data)
					newsize -= rate
					if(hash_flag):
						print("#", end = "")
				f.close()
			t_end = time()
			net_time = t_end - t_start
			if(d_size != 0):
				print("{} bytes received in {} seconds".format(d_size, net_time))
			else:
				print("Bad file name")
			continue

		#To upload files on server
		elif(org_cmnd[0] == "put"):
			if(anonymous == 0):
				t_start = time()
				
				if(pasv_flag == False):
					connectionSock = createData(controlSock)
				else:
					data = controlSock.recv(1024).decode()
					data = (data + " " + serverName)  		
					connectionSock, dataPort = connectData(data)

				try:
					obj = os.stat(org_cmnd[1])
				except:
					controlSock.send("0".encode())
					closeData(connectionSock)
					continue
				path = os.getcwd() + "/" + org_cmnd[1]
				if(os.path.isdir(path)):
					controlSock.send("0".encode())
					continue
				controlSock.send(str(obj.st_size).encode())
				with open(org_cmnd[1], "rb") as f:
					data = f.read()
					connectionSock.sendall(data)
				f.close()
				closeData(connectionSock)
				t_end = time()
				net_time = t_end - t_start
				print("{} bytes sent in {} seconds".format(obj.st_size, net_time))
			continue

		#To get multiple files from server
		elif(org_cmnd[0] == "mget"):
			length = len(org_cmnd) - 1
			i = 1
			t_start = time()
			while(length):
				
				if(pasv_flag == False):
					connectionSock = createData(controlSock)
				else:
					data = controlSock.recv(1024).decode()
					data = (data + " " + serverName)  		
					connectionSock, dataPort = connectData(data)
		
				size = int(controlSock.recv(1024).decode())
				if(size):
					f = open(org_cmnd[i], "ab")
					while (size > 0):
						data = connectionSock.recv(rate)				
						f.write(data)
						size -= rate
						if(hash_flag):
							print("#", end = "")
					f.close()
					i += 1
					print("\n", end = "")
				closeData(connectionSock)
				
				length -= 1
			t_end = time()
			net_time = t_end - t_start
			print("{} files received in {} seconds".format(i - 1, net_time))	
			continue

		#To upload multiple files on server
		elif(org_cmnd[0] == "mput"):
			if(anonymous == 0):
				length = len(org_cmnd) - 1
				i = 1
				j = 1
				t_start = time()
				while(length):
					length -= 1
					
					if(pasv_flag == False):
						connectionSock = createData(controlSock)
					else:
						data = controlSock.recv(1024).decode()
						data = (data + " " + serverName)  		
						connectionSock, dataPort = connectData(data)

					try:
						obj = os.stat(org_cmnd[i])
					except:
						controlSock.send("0".encode())
						i += 1
						closeData(connectionSock)
						continue
					path = os.getcwd() + "/" + org_cmnd[i]
					if(os.path.isdir(path)):
						controlSock.send("0".encode())
						i += 1
						continue
					controlSock.send(str(obj.st_size).encode())
					with open(org_cmnd[i], "rb") as f:
						data = f.read()
						connectionSock.sendall(data)
					f.close()
					closeData(connectionSock)
					i += 1
					j += 1
				t_end = time()
				net_time = t_end - t_start
				print("{} files sent in {} seconds".format(j - 1, net_time))	
			continue
		
		#Toggle hash-sign (``#'') printing for each transferred data block, but only in the absence of an argument.
		elif(org_cmnd[0] == "hash"):
			try:
				rate = int(org_cmnd[1])
			except:
				rate = 1024
			finally:			
				hash_flag = not (hash_flag)
				print("hash mark printing per ({} bytes/hash mark)".format(rate))
		else:
			print("Command not available")
			
if __name__ == '__main__':
	Main()
