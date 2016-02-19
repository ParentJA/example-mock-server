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
