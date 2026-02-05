# Lab 2

## Team Members

- team member 1: Abhigya Goel
- team member 2: nobody

## tcp_server.c question answers

1. Argc: integer, Argv: array. Argc gives the amount of arguments passed in a command line, while Argv is an array containing strings that become arguments in the command line. Argv also contains the port number but as a string.

2. UNIX File Descriptor: an integer that uniquely identifies an open file. File Descriptor Table: a data structure used by a computer's OS to keep track of all open files and their associated file descriptors.

3. A struct is a user-defined data type in that allows for grouping of variables of different types under a single name. The structure of sockaddr_in includes address family, port number, and IP address.

4. Input: domain (specifies the protocol family), type (specifies the communication type), protocol (specifies a particular protocol to be used with the socket).

Return value: on success, a non-negative integer that represents the file descriptor for the new socket. On error, -1.

5. Input for bind(): socket file descriptor, pointer to sockaddr structure, size of the sockaddr structure. Input for listen(): socket file descriptor, maximum number of pending connections.

6. While(1) creates an infinite loop, which lets the server continuously accept/handle incoming connections.

If multiple simultaneous connections occur, the server may struggle to manage them effectively. This might lead to delays/dropped connections, as it processes connections individually and sequentially.

7. Fork() creates a new process by duplicating the calling process. It returns 0 in the child process and the PID of the child in the parent process. In this file, fork() can be used to create a new process for each incoming connection, which then allows multiple connections to be handled concurrently.

8. A system call is something that allows a program to request a service from the OS's kernel. It gives an interface between user-space applications and the OS, and allows for tasks like file operations, process management, and network communication.

## Lab Question Answers

0. First questions (QA.1 to QA.2):

- Became less reliable because there was packet loss, stifling information flow and preventing a successful transfer of all numbers or data

- It responded every time, but slower. This is because TCP establishes a connection between sockets and ensures packets flow through, regardless of speed.

1. Why does the server need to be running before the client tries to connect?

- There has to be something for the client to connect to.

2. What changed when you ran the server on the Raspberry Pi instead of on your own machine? What stayed the same?

- Server address and location, but the communication method and output remained the same.

3. When packet loss was added, why did TCP messages arrive more slowly even though none were missing?

- TCP contains a handshake that ensures packets are sent, albeit slowly.

4. When you added 50% packet loss and sent the same numbers using UDP and TCP, what difference did you notice, and why did that happen?

- UDP: some data loss, due to lack of verification or acknowledgement mechanism. TCP: no data loss, just slower data stream due to presence of handshake/verification mechanism.

5. Based on what you observed, when might UDP still be a better choice than TCP?

- When speed takes priority over the transfer of data/reliability.

6. If you had to summarize this lab in one idea, what was it trying to teach you about networked programs?

- The different types of programs and what their capabilities are.

If the client cannot connect to the Raspberry Pi server, give two different types of things that could be wrong.

- The IP address or the port. The client and server may not be on the same wifi address.

In the tcp_server.c code, the data transfer logic is placed inside a while(1) loop. What is the purpose of this loop?

- Its to keep an infinite loop going so there is a constant stream instead of a singular data point entering the server.

If you change the HOST variable in your client code to "127.0.0.1" (localhost) but leave the server running on the Raspberry Pi, will the connection work? Why or why not?

- No, you must connect to the Pi and not the host machine, by using the Pi's specific address.

In the Python client (tcp_client.py), why must you call .encode() on the user input before sending it?

- This function turns the data stream from strings to transferable raw byte data that can be transmitted over the server. This is because sockets don't transfer strings, just data.

...
