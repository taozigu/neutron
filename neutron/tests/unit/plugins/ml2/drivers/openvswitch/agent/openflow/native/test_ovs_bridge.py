# Copyright (c) 2016 Mirantis, Inc.
# All Rights Reserved.
#
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

import mock

from neutron.tests.unit.plugins.ml2.drivers.openvswitch.agent \
    import ovs_test_base


class OVSAgentBridgeTestCase(ovs_test_base.OVSRyuTestBase):
    def test__get_dp(self):
        mock.patch(
            'neutron.agent.common.ovs_lib.OVSBridge.get_datapath_id',
            return_value="3e9").start()
        mock.patch(
            "neutron.plugins.ml2.drivers.openvswitch.agent.openflow.native."
            "ofswitch.OpenFlowSwitchMixin._get_dp_by_dpid",
            side_effect=RuntimeError).start()
        br = self.br_int_cls('br-int')
        br._cached_dpid = int("3e9", 16)
        # make sure it correctly raises RuntimeError, not UnboundLocalError as
        # in LP https://bugs.launchpad.net/neutron/+bug/1588042
        self.assertRaises(RuntimeError, br._get_dp)
