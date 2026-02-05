/* A simple server in the internet domain using TCP
 * Answer the questions below in your writeup
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>

void error(const char *msg)
{
    perror(msg);
    exit(1);
}

int main(int argc, char *argv[])
{
    /* 1. What is argc and *argv[]?
     * Argc: integer, Argv: array. Argc gives the amount of arguments passed in a command line, while
       Argv is an array containing strings that become arguments in the command line. Argv also contains
       the port number but as a string.
     */
    int sockfd, newsockfd, portno;
    /* 2. What is a UNIX file descriptor and file descriptor table?
     * UNIX File Descriptor: an integer that uniquely identifies an open file.
       File Descriptor Table: a data structure used by a computer's OS to keep track of all open files and
       their associated file descriptors.
     */
    socklen_t clilen;

    struct sockaddr_in serv_addr, cli_addr;
    /* 3. What is a struct? What's the structure of sockaddr_in?
     * A struct is a user-defined data type in that allows for grouping of variables
       of different types under a single name.

       The structure of sockaddr_in includes address family, port number, and IP address.
     */

    int n;
    if (argc < 2)
    {
        fprintf(stderr, "ERROR, no port provided\n");
        exit(1);
    }

    sockfd = socket(AF_INET, SOCK_STREAM, 0);
    /* 4. What are the input parameters and return value of socket()
     *  Input: domain (specifies the protocol family), type (specifies the communication type),
       protocol (specifies a particular protocol to be used with the socket)

       Return value: on success, a non-negative integer that represents the
       file descriptor for the new socket.
       On error, -1.
     */

    if (sockfd < 0)
        error("ERROR opening socket");
    bzero((char *)&serv_addr, sizeof(serv_addr));
    portno = atoi(argv[1]);
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_addr.s_addr = INADDR_ANY;
    serv_addr.sin_port = htons(portno);

    if (bind(sockfd, (struct sockaddr *)&serv_addr,
             sizeof(serv_addr)) < 0)
        error("ERROR on binding");
    /* 5. What are the input parameters of bind() and listen()?
     *  Input for bind(): socket file descriptor, pointer to sockaddr structure, size of the sockaddr structure

        Input for listen(): socket file descriptor, maximum number of pending connections
     */

    listen(sockfd, 5);
    clilen = sizeof(cli_addr);

    while (1)
    {
        /* 6.  Why use while(1)? Based on the code below, what problems might occur if there are multiple simultaneous connections to handle?
        *
           While(1) creates an infinite loop, which lets the server continuously
           accept/handle incoming connections.

           If multiple simultaneous connections occur, the server may struggle to
           manage them effectively. This might lead to delays/dropped connections,
           as it processes connections individually and sequentially.
        */

        char buffer[256];
        newsockfd = accept(sockfd,
                           (struct sockaddr *)&cli_addr,
                           &clilen);
        /* 7. Research how the command fork() works. How can it be applied here to better handle multiple connections?
             * Fork() creates a new process by duplicating the calling process.
               It returns 0 in the child process and the PID of the child in the parent process.

             * In this file, fork() can be used to create a new process for each incoming connection,
               which then allows multiple connections to be handled concurrently.
             */

        if (newsockfd < 0)
            error("ERROR on accept");
        bzero(buffer, 256);

        n = read(newsockfd, buffer, 255);
        if (n < 0)
            error("ERROR reading from socket");
        // printf("Here is the message: %s\n",buffer);
        n = write(newsockfd, "I got your message", 18);
        if (n < 0)
            error("ERROR writing to socket");
        close(newsockfd);
    }
    close(sockfd);
    return 0;
}

/* This program makes several system calls such as 'bind', and 'listen.' What exactly is a system call?
 *
    A system call is something that allows a program to request a service from the OS's kernel.
    It gives an interface between user-space applications and the OS, and allows for tasks like
    file operations, process management, and network communication.
 */