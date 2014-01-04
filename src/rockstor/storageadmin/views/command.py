"""
Copyright (c) 2012-2013 RockStor, Inc. <http://rockstor.com>
This file is part of RockStor.

RockStor is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published
by the Free Software Foundation; either version 2 of the License,
or (at your option) any later version.

RockStor is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

"""
System info etc..
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import (BasicAuthentication,
                                           SessionAuthentication)
from storageadmin.auth import DigestAuthentication
from rest_framework.permissions import IsAuthenticated
from system.osi import (uptime, refresh_nfs_exports, update_check, update_run)
from fs.btrfs import (is_share_mounted, mount_share)
from system.ssh import (sftp_mount_map, sftp_mount)
from storageadmin.models import (Share, Disk, NFSExport, SFTP)
from nfs_helpers import create_nfs_export_input
from storageadmin.util import handle_exception
from datetime import datetime
from django.utils.timezone import utc
from django.conf import settings

import logging
logger = logging.getLogger(__name__)


class CommandView(APIView):
    authentication_classes = (DigestAuthentication, SessionAuthentication,
                              BasicAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, command):
        if (command == 'bootstrap'):
            logger.info('bootstrapping...')
            try:
                for share in Share.objects.all():
                    if (not is_share_mounted(share.name)):
                        mnt_pt = ('%s%s' % (settings.MNT_PT, share.name))
                        pool_device = Disk.objects.filter(pool=share.pool)[0].name
                        mount_share(share.subvol_name, pool_device, mnt_pt)
            except Exception, e:
                e_msg = ('Unable to mount all shares during bootstrap.')
                logger.error(e_msg)
                logger.exception(e)
                handle_exception(Exception(e_msg), request)

            try:
                mnt_map = sftp_mount_map(settings.SFTP_MNT_ROOT)
                logger.info('mnt map = %s' % mnt_map)
                for sftpo in SFTP.objects.all():
                    sftp_mount(sftpo.share, settings.MNT_PT,
                               settings.SFTP_MNT_ROOT, mnt_map, sftpo.editable)
            except Exception, e:
                e_msg = ('Unable to export all sftp shares due to a system'
                         ' error')
                logger.error(e_msg)
                logger.exception(e)
                handle_exception(Exception(e_msg), request)

            try:
                exports = create_nfs_export_input(NFSExport.objects.all())
                logger.info('export = %s' % exports)
                refresh_nfs_exports(exports)
            except Exception, e:
                e_msg = ('Unable to export all nfs shares due to a system error')
                logger.error(e_msg)
                logger.exception(e)
                handle_exception(Exception(e_msg), request)

            return Response()

        elif (command == 'utcnow'):
            return Response(datetime.utcnow().replace(tzinfo=utc))

        elif (command == 'uptime'):
            return Response(uptime())

        elif (command == 'update-check'):
            try:
                return Response(update_check())
            except Exception, e:
                e_msg = ('Unalbe to check update due to a system error')
                logger.exception(e)
                handle_exception(Exception(e_msg), request)

        elif (command == 'update'):
            try:
                update_run()
                return Response('Done')
            except Exception, e:
                e_msg = ('Update failed due to a system error')
                logger.exception(e)
                handle_exception(Exception(e_msg), request)
