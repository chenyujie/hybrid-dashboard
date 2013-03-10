# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011-2012 OpenStack LLC.
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

import json
from oslo.config import cfg

import webob.exc

from portas.openstack.common import wsgi
import portas.context
import portas.openstack.common.log as logging

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class BaseContextMiddleware(wsgi.Middleware):
    def process_response(self, resp):
        try:
            request_id = resp.request.context.request_id
        except AttributeError:
            LOG.warn(_('Unable to retrieve request id from context'))
        else:
            resp.headers['x-openstack-request-id'] = 'req-%s' % request_id
        return resp


class ContextMiddleware(BaseContextMiddleware):
    def process_request(self, req):
        """Convert authentication information into a request context

        Generate a portas.context.RequestContext object from the available
        authentication headers and store on the 'context' attribute
        of the req object.

        :param req: wsgi request object that will be given the context object
        :raises webob.exc.HTTPUnauthorized: when value of the X-Identity-Status
                                            header is not 'Confirmed' and
                                            anonymous access is disallowed
        """
        if req.headers.get('X-Identity-Status') == 'Confirmed':
            roles_header = req.headers.get('X-Roles', '')
            roles = [r.strip().lower() for r in roles_header.split(',')]

            #NOTE(bcwaldon): This header is deprecated in favor of X-Auth-Token
            deprecated_token = req.headers.get('X-Storage-Token')

            service_catalog = None
            if req.headers.get('X-Service-Catalog') is not None:
                try:
                    catalog_header = req.headers.get('X-Service-Catalog')
                    service_catalog = json.loads(catalog_header)
                except ValueError:
                    raise webob.exc.HTTPInternalServerError(
                        _('Invalid service catalog json.'))

            kwargs = {
                'user': req.headers.get('X-User-Id'),
                'tenant': req.headers.get('X-Tenant-Id'),
                'roles': roles,
                'auth_tok': req.headers.get('X-Auth-Token', deprecated_token),
                'service_catalog': service_catalog,
                'session': req.headers.get('X-Configuration-Session')
                }
            req.context = portas.context.RequestContext(**kwargs)
        else:
            raise webob.exc.HTTPUnauthorized()

    @classmethod
    def factory(cls, global_conf, **local_conf):
        def filter(app):
            return cls(app)
        return filter