#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import uuid

from six.moves import http_client

from keystone.common import provider_api
import keystone.conf
from keystone.tests.common import auth as common_auth
from keystone.tests import unit
from keystone.tests.unit import base_classes
from keystone.tests.unit import ksfixtures

CONF = keystone.conf.CONF
PROVIDERS = provider_api.ProviderAPIs


class _SystemUserRoleTests(object):
    """Common default functionality for all system users."""

    def test_user_can_list_roles(self):
        PROVIDERS.role_api.create_role(uuid.uuid4().hex, unit.new_role_ref())

        with self.test_client() as c:
            r = c.get('/v3/roles', headers=self.headers)
            # With bootstrap setup and the role we just created, there should
            # be four roles present in the deployment. Bootstrap creates
            # ``admin``, ``member``, and ``reader``.
            self.assertEqual(4, len(r.json['roles']))

    def test_user_can_get_a_role(self):
        role = PROVIDERS.role_api.create_role(
            uuid.uuid4().hex, unit.new_role_ref()
        )

        with self.test_client() as c:
            r = c.get('/v3/roles/%s' % role['id'], headers=self.headers)
            self.assertEqual(role['id'], r.json['role']['id'])


class SystemReaderTests(base_classes.TestCaseWithBootstrap,
                        common_auth.AuthTestMixin,
                        _SystemUserRoleTests):

    def setUp(self):
        super(SystemReaderTests, self).setUp()
        self.loadapp()
        self.useFixture(ksfixtures.Policy(self.config_fixture))
        self.config_fixture.config(group='oslo_policy', enforce_scope=True)

        system_reader = unit.new_user_ref(
            domain_id=CONF.identity.default_domain_id
        )
        self.user_id = PROVIDERS.identity_api.create_user(
            system_reader
        )['id']
        PROVIDERS.assignment_api.create_system_grant_for_user(
            self.user_id, self.bootstrapper.reader_role_id
        )

        auth = self.build_authentication_request(
            user_id=self.user_id, password=system_reader['password'],
            system=True
        )

        # Grab a token using the persona we're testing and prepare headers
        # for requests we'll be making in the tests.
        with self.test_client() as c:
            r = c.post('/v3/auth/tokens', json=auth)
            self.token_id = r.headers['X-Subject-Token']
            self.headers = {'X-Auth-Token': self.token_id}

    def test_user_cannot_create_roles(self):
        create = {'role': unit.new_role_ref()}

        with self.test_client() as c:
            c.post(
                '/v3/roles', json=create, headers=self.headers,
                expected_status_code=http_client.FORBIDDEN
            )

    def test_user_cannot_update_roles(self):
        role = PROVIDERS.role_api.create_role(
            uuid.uuid4().hex, unit.new_role_ref()
        )

        update = {'role': {'description': uuid.uuid4().hex}}

        with self.test_client() as c:
            c.patch(
                '/v3/roles/%s' % role['id'], json=update, headers=self.headers,
                expected_status_code=http_client.FORBIDDEN
            )

    def test_user_cannot_delete_roles(self):
        role = PROVIDERS.role_api.create_role(
            uuid.uuid4().hex, unit.new_role_ref()
        )

        with self.test_client() as c:
            c.delete(
                '/v3/roles/%s' % role['id'], headers=self.headers,
                expected_status_code=http_client.FORBIDDEN
            )