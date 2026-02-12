- Question 1: Why are RESTful APIs scalable?

Requests are stateless and caches are managed partially, so servers
spread out traffic without the need to figure out individual clients'
session's states.

- Question 2: According to the definition of “resources” provided in the
  AWS article above, what are the resources the mail server is providing to
  clients?

Any of the mail entries or the messages that are stored in the system, containing
information like the mail ID, username, mail subject, mail body.

- Question 3: What is one common REST Method not used in our mail
  server? How could we extend our mail server to use this method?

PUT, which could be very useful since you could update any existing emails.

- Question 4: Why are API keys used for many RESTful APIs? What purpose
  do they serve?

They allow for a unique identifier that can be used to authenticate anyone
attempting to use the service, serving as a powerful tool for security.

Resources Used: AWS article: https://aws.amazon.com/what-is/restful-api/
