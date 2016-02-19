# Third-party imports...
from lettuce import step, world
from nose.tools import assert_dict_contains_subset, assert_is_instance, assert_true

# Local imports...
from example.services import get_users


@step(r'I send a real request')
def send_request(step):
    world.response = get_users()


@step(r'I get a real response')
def get_response(step):
    assert_dict_contains_subset({'Content-Type': 'application/json; charset=utf-8'}, world.response.headers)
    assert_true(world.response.ok)
    assert_is_instance(world.response.json(), list)
