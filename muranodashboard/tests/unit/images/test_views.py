# Copyright (c) 2016 AT&T Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock
import testtools

from horizon import exceptions

from muranodashboard.images import views


class TestImagesForms(testtools.TestCase):
    def setUp(self):
        super(TestImagesForms, self).setUp()
        self.mock_request = mock.MagicMock()
        self.miv = views.MarkedImagesView(request=self.mock_request)

    @mock.patch.object(views, 'reverse')
    def test_get_data_error(self, mock_reverse):
        self.assertRaises(exceptions.Http302, self.miv.get_data)
        mock_reverse.assert_called_once_with('horizon:app-catalog:'
                                             'catalog:index')
