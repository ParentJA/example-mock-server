# Testing Third-Party APIs with Mock Servers

**By Jason Parent**

Every popular product has an API that allows your app to use its services. I use external APIs in almost all of my projects and chances are good that you do too. So many useful services exist that it is difficult to have a great app without leveraging what they offer.

Despite being so useful, external APIs can be a pain to test. When you hit an actual API, your tests are at the mercy of the server. You will likely encounter one or more the following pain points:
- The request-response cycle can take several seconds. That might not seem like much at first, but the time compounds with each test. Imagine calling an API 10, 50, or 100 times when testing your entire application. 
- The API server may be unreachable. Maybe the server is down for maintenance. Maybe it failed with an error and a development team is working to get it functional again. Do you really want the success of your tests to rely on the health of a server you don't control? 

Your tests shouldn't assess whether an API server is running; they should test whether your code is operating as expected. This tutorial will teach you how to mock an API server to test your Python code that interacts with external services.

## Setup

Download and install a tool that lets you create isolated Python environments on your local machine. I prefer <a href="https://virtualenvwrapper.readthedocs.org/en/latest/install.html">virtualenvwrapper</a>. Make a virtual environment and install the required packages outlined below. Navigate to a directory where you keep your projects and start a new Django project.

```bash
local:~ user$ mkvirtualenv example
(example)local:~ user$ pip install Django django-nose lettuce mock requests
(example)local:~ user$ cd ~/Projects
(example)local:Projects user$ django-admin.py startproject example && cd example
```

Add ```lettuce.django``` and ```example``` to the ```INSTALLED_APPS``` iterable in the ```settings.py``` file at the app root.

**example/example/settings.py**

```python
INSTALLED_APPS = (
    ...
    'lettuce.django',
    'example',
)
```

## Sanity Check: Testing the Real API

Before you mock the API server, make sure the real API is actually working properly. At some point, you are going to have to test the real API. In general, you want to do this selectively and not burden your automated tests with the responsibility. In the following examples, you will be using the <a href="http://jsonplaceholder.typicode.com/">JSONPlaceholder</a> fake online REST API.

Send a request to the API to make sure you get a response.

```bash
(example)local:example user$ curl -X GET 'http://jsonplaceholder.typicode.com/users'
```

When you send a valid request to the API, you expect it to return a valid response. Write a test that describes this behavior.

**example/example/features/real_server.feature**

```cucumber
Feature: Communicating with the real API

  @real
  Scenario: Hitting a URL on the real server

    When I send a real request
    Then I get a real response
```

Notice the ```@real``` tag attached to the scenario. Using a tag allows you to selectively control how the marked scenario is tested. Marked scenarios can be excluded from tests or tested exclusively using the ```--tag``` argument with ```harvest``` as demonstrated below.

Next, write the ```step``` functions that attach your tests statements to the logic that controls them. Keep the logic simple at first. The following code tests a successful request-response cycle.

**example/example/features/real_server_steps.py**

```python
# Third-party imports...
from lettuce import step, world
from nose.tools import assert_true
import requests


@step(r'I send a real request')
def send_request(step):
    # Send a request to the API server and store the response.
    world.response = requests.get('http://jsonplaceholder.typicode.com/users')


@step(r'I get a real response')
def get_response(step):
    # Confirm that the request-response cycle completed successfully.
    assert_true(world.response.ok)
```

Run the tests and see that they pass. You can control how much information is written to the console when the tests run using the ```--verbosity``` argument. I prefer to see a moderate level of information about my tests. See the <a href="http://lettuce.it/reference/cli.html#verbosity-levels">Lettuce documentation</a> for more information about verbosity levels.

You added a ```@real``` tag to a scenario in a previous step. Add a ```--tag=real``` argument in your command line to *only* run scenarios marked with the ```@real``` tag. Add a ```-``` in front of the argument ```--tag=-real``` to run *every scenario except* scenarios tagged with ```@real```. Finally, if you do not pass any tag arguments, your tags will be ignored and all scenarios will run.

```bash
(example)local:example user$ python manage.py harvest --verbosity=2
```

## Testing the Mock API

Once you confirm that the real API is working as expected, you can program your mock server. Write a test that describes the behavior. Notice that it looks almost identical to the real API test.

**example/example/features/mock_server.feature**

```cucumber
Feature: Mock server

  Scenario: Hitting a URL on the mock server

    When I send a mock request
    Then I get a mock response
```

Here is how to create a mock server in Python. First, create a subclass of ```BaseHTTPRequestHandler```. This class captures the request and constructs the response to return. Override the ```do_GET()``` function to craft the response for an HTTP GET request. In this case, just return an OK status. Next, write a function to get an available port number for the mock server to use. 

The next block of code actually configures the server. Notice how the code instantiates a ```HTTPServer``` instance and passes it a port number and a handler. Next, create a thread, so that the server can be run asynchronously and your main program thread can communicate with it. Make the thread a daemon, which tells the thread to stop when the main program exits. Finally, start the thread to serve the mock server forever (until the tests finish).

Notice that all of the code lives within a ```feature_setup()``` function, which is decorated with ```@before.each_feature```. This bit of code ensures that the mock server will run before the feature is tested.

Finally, create similar step definitions to the real API scenarios, except test the mock server URL instead of the actual API URL.

**example/example/features/mock_server_steps.py**

```python
# Standard library imports...
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import socket
from threading import Thread

# Third-party imports...
from lettuce import before, step, world
from nose.tools import assert_true
import requests


class MockServerRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Process an HTTP GET request and return a response with an HTTP 200 status.
        self.send_response(requests.codes.ok)
        return


def get_free_port():
    s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    address, port = s.getsockname()
    s.close()
    return port


@before.each_feature
def feature_setup(feature):
    # Configure mock server.
    world.mock_server_port = get_free_port()
    world.mock_server = HTTPServer(('localhost', world.mock_server_port), MockServerRequestHandler)

    # Start running mock server in a separate thread. 
    # Daemon threads automatically shut down when the main process exits.
    world.mock_server_thread = Thread(target=world.mock_server.serve_forever)
    world.mock_server_thread.setDaemon(True)
    world.mock_server_thread.start()


@step(r'I send a mock request')
def send_request(step):
    url = 'http://localhost:{port}/users'.format(port=world.mock_server_port)
    world.response = requests.get(url)


@step(r'I get a mock response')
def get_response(step):
    assert_true(world.response.ok)
```

Run the tests and watch them pass.

```bash
(example)local:example user$ python manage.py harvest --verbosity=2
```

## Testing a Service that Hits the API

You probably want to call more than one API endpoint in your code. As you design your app, you will likely create service functions to send requests to an API and then process the responses in some way. Maybe you will store the response data in a database. Or you will pass the data to a user interface.

Refactor your code to pull the hardcoded API base URL into a setting. Add this variable to your Django project ```settings.py``` file.

**example/example/settings.py**

```python
BASE_URL = 'http://jsonplaceholder.typicode.com'
```

Next, encapsulate the logic to retrieve users from the API into a function. Notice how new URLs can be created by joining a URL path to the base.

**example/example/services.py**

```python
# Standard library imports...
from urlparse import urljoin

# Third-party imports...
import requests

# Django imports...
from django.conf import settings

BASE_URL = getattr(settings, 'BASE_URL')
USERS_URL = urljoin(BASE_URL, 'users')


def get_users():
    response = requests.get(USERS_URL)
    if response.ok:
        return response
    else:
        return None
```

Move the mock server code from the feature file to a new Python file, so that it can easily be reused. Add conditional logic to the request handler to check which API endpoint the HTTP request is targeting. Beef up the response by adding some simple header information and a basic response payload. The server creation and kick off code can be encapsulated in a convenience method, ```start_mock_server()```.

**example/example/features/mocks.py**

```python
# Standard library imports...
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import json
import re
import socket
from threading import Thread

# Third-party imports...
import requests


class MockServerRequestHandler(BaseHTTPRequestHandler):
    USERS_PATTERN = re.compile(r'/users')

    def do_GET(self):
        if re.search(self.USERS_PATTERN, self.path):
            # Add response status code.
            self.send_response(requests.codes.ok)

            # Add response headers.
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()

            # Add response content.
            response_content = json.dumps([])
            self.wfile.write(response_content)
            return


def get_free_port():
    s = socket.socket(socket.AF_INET, type=socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    address, port = s.getsockname()
    s.close()
    return port


def start_mock_server(port):
    mock_server = HTTPServer(('localhost', port), MockServerRequestHandler)
    mock_server_thread = Thread(target=mock_server.serve_forever)
    mock_server_thread.setDaemon(True)
    mock_server_thread.start()
```

With your changes to the logic completed, alter the tests to use the new service function. Update the tests to check the increased information that is being passed back from the server.

**example/example/features/real_server_steps.py**

```python
# Third-party imports...
from lettuce import step, world
from nose.tools import assert_dict_contains_subset, assert_list_equal, assert_true

# Local imports...
from example.services import get_users


@step(r'I send a real request')
def send_request(step):
    world.response = get_users()


@step(r'I get a real response')
def get_response(step):
    assert_dict_contains_subset({'Content-Type': 'application/json; charset=utf-8'}, world.response.headers)
    assert_true(world.response.ok)
    assert_list_equal(world.response.json(), [])
```

**example/example/features/mock_server_steps.py**

```python
# Third-party imports...
from lettuce import before, step, world
from mock import patch
from nose.tools import assert_dict_contains_subset, assert_list_equal, assert_true

# Local imports...
from example.features.mocks import get_free_port, start_mock_server
from example.services import get_users


@before.each_feature
def feature_setup(feature):
    world.mock_server_port = get_free_port()
    start_mock_server(world.mock_server_port)


@step(r'I send a mock request')
def send_request(step):
    mock_users_url = 'http://localhost:{port}/users'.format(port=world.mock_server_port)

    # Patch USERS_URL so that the service uses the mock server URL instead of the real URL.
    with patch.dict('example.services.__dict__', {'USERS_URL': mock_users_url}):
        world.response = get_users()


@step(r'I get a mock response')
def get_response(step):
    assert_dict_contains_subset({'Content-Type': 'application/json; charset=utf-8'}, world.response.headers)
    assert_true(world.response.ok)
    assert_list_equal(world.response.json(), [])
```

Notice a new technique being used in the ```mock_server_steps.py``` code. The ```world.response = get_users()``` line is wrapped with a ```patch.dict()``` function from the Mock library. What does this statement do? Remember, you moved the ```requests.get()``` function from the feature logic to the ```get_users()``` service function. Internally, ```get_users()``` calls ```requests.get()``` using the ```USERS_URL``` variable. The ```patch.dict()``` function temporarily replaces the value of the ```USERS_URL``` variable. In fact, it does so only within the scope of the ```with``` statement. After that code runs, the ```USERS_URL``` variable is restored to its original value. This code *patches* the URL to use the mock server address.

Run the tests and watch them pass.

```bash
(example)local:example user$ python manage.py harvest --verbosity=2
```

## Next Steps

Now that you have created a mock server to test your external API calls, you can apply this knowledge to your own projects. Build upon the simple tests created here. Expand the functionality of the handler to mimic the behavior of the real API more closely.

Try the following exercises to level up:
- Return a response with a status of HTTP 404 (not found) if a request is sent with an unknown path.
- Return a response with a status of HTTP 405 (method not allowed) if a request is sent with a method that is not allowed (POST, DELETE, UPDATE).
- Return actual user data for a valid request to ```/users```.
- Write tests to capture those scenarios.

