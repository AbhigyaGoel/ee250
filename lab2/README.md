# Lab 2

## Team Members

- team member 1: Abhigya Goel
- team member 2

## Lab Question Answers

0. First questions:

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
