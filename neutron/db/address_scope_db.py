# Copyright (c) 2015 Huawei Technologies Co.,LTD.
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

from neutron_lib import constants
from oslo_utils import uuidutils

from neutron._i18n import _
from neutron.api.v2 import attributes as attr
from neutron.common import _deprecate
from neutron.db import _utils as db_utils
from neutron.db import api as db_api
from neutron.db import db_base_plugin_v2
from neutron.db.models import address_scope as address_scope_model
from neutron.extensions import address_scope as ext_address_scope
from neutron.objects import address_scope as obj_addr_scope
from neutron.objects import base as base_obj
from neutron.objects import subnetpool as subnetpool_obj


_deprecate._moved_global('AddressScope', new_module=address_scope_model)


class AddressScopeDbMixin(ext_address_scope.AddressScopePluginBase):
    """Mixin class to add address scope to db_base_plugin_v2."""

    __native_bulk_support = True

    @staticmethod
    def _make_address_scope_dict(address_scope, fields=None):
        res = {'id': address_scope['id'],
               'name': address_scope['name'],
               'tenant_id': address_scope['tenant_id'],
               'shared': address_scope['shared'],
               'ip_version': address_scope['ip_version']}
        return db_utils.resource_fields(res, fields)

    def _get_address_scope(self, context, id):
        obj = obj_addr_scope.AddressScope.get_object(context, id=id)
        if obj is None:
            raise ext_address_scope.AddressScopeNotFound(address_scope_id=id)
        return obj

    def is_address_scope_owned_by_tenant(self, context, id):
        """Check if address scope id is owned by the tenant or not.

        AddressScopeNotFound is raised if the
          - address scope id doesn't exist or
          - if the (unshared) address scope id is not owned by this tenant.

        @return Returns true if the user is admin or tenant is owner
                Returns false if the address scope id is shared and not
                owned by the tenant.
        """
        address_scope = self._get_address_scope(context, id)
        return context.is_admin or (
            address_scope.tenant_id == context.tenant_id)

    def get_ip_version_for_address_scope(self, context, id):
        address_scope = self._get_address_scope(context, id)
        return address_scope.ip_version

    def create_address_scope(self, context, address_scope):
        """Create an address scope."""
        a_s = address_scope['address_scope']
        address_scope_id = a_s.get('id') or uuidutils.generate_uuid()
        pool_args = {'tenant_id': a_s['tenant_id'],
                     'id': address_scope_id,
                     'name': a_s['name'],
                     'shared': a_s['shared'],
                     'ip_version': a_s['ip_version']}
        address_scope = obj_addr_scope.AddressScope(context, **pool_args)
        address_scope.create()
        return self._make_address_scope_dict(address_scope)

    def update_address_scope(self, context, id, address_scope):
        a_s = address_scope['address_scope']
        address_scope = self._get_address_scope(context, id)
        if address_scope.shared and not a_s.get('shared', True):
            reason = _("Shared address scope can't be unshared")
            raise ext_address_scope.AddressScopeUpdateError(
                address_scope_id=id, reason=reason)

        address_scope.update_fields(a_s)
        address_scope.update()
        return self._make_address_scope_dict(address_scope)

    def get_address_scope(self, context, id, fields=None):
        address_scope = self._get_address_scope(context, id)
        return self._make_address_scope_dict(address_scope, fields)

    def get_address_scopes(self, context, filters=None, fields=None,
                           sorts=None, limit=None, marker=None,
                           page_reverse=False):
        pager = base_obj.Pager(sorts, limit, page_reverse, marker)
        address_scopes = obj_addr_scope.AddressScope.get_objects(
            context, _pager=pager, **filters)

        return [
            self._make_address_scope_dict(addr_scope, fields)
            for addr_scope in address_scopes
        ]

    def get_address_scopes_count(self, context, filters=None):
        return obj_addr_scope.AddressScope.count(context, **filters)

    def delete_address_scope(self, context, id):
        with db_api.context_manager.writer.using(context):
            if subnetpool_obj.SubnetPool.get_objects(context,
                                                     address_scope_id=id):
                raise ext_address_scope.AddressScopeInUse(address_scope_id=id)
            address_scope = self._get_address_scope(context, id)
            address_scope.delete()

    def _extend_network_dict_address_scope(self, network_res, network_db):
        network_res[ext_address_scope.IPV4_ADDRESS_SCOPE] = None
        network_res[ext_address_scope.IPV6_ADDRESS_SCOPE] = None
        subnetpools = {subnet.subnetpool for subnet in network_db.subnets
                       if subnet.subnetpool}
        for subnetpool in subnetpools:
            # A network will be constrained to only one subnetpool per address
            # family. Retrieve the address scope of subnetpools as the address
            # scopes of network.
            as_id = subnetpool[ext_address_scope.ADDRESS_SCOPE_ID]
            if subnetpool['ip_version'] == constants.IP_VERSION_4:
                network_res[ext_address_scope.IPV4_ADDRESS_SCOPE] = as_id
            if subnetpool['ip_version'] == constants.IP_VERSION_6:
                network_res[ext_address_scope.IPV6_ADDRESS_SCOPE] = as_id
        return network_res

    db_base_plugin_v2.NeutronDbPluginV2.register_dict_extend_funcs(
        attr.NETWORKS, ['_extend_network_dict_address_scope'])


_deprecate._MovedGlobals()
