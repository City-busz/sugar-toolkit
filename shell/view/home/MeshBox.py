# Copyright (C) 2006, Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import random

import hippo
import gobject

from sugar.graphics.spreadbox import SpreadBox
from sugar.graphics.snowflakebox import SnowflakeBox
from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics import color
from sugar.graphics import canvasicon
from model import accesspointmodel
from hardware import hardwaremanager
from view.BuddyIcon import BuddyIcon
from view.pulsingicon import PulsingIcon

_ICON_NAME = 'device-network-wireless'

class AccessPointView(PulsingIcon):
    def __init__(self, model):
        PulsingIcon.__init__(self)
        self._model = model

        self.connect('activated', self._activate_cb)

        model.connect('notify::strength', self._strength_changed_cb)
        model.connect('notify::name', self._name_changed_cb)
        model.connect('notify::state', self._state_changed_cb)

        self.props.colors = [
            [ None, None ],
            [ color.ICON_FILL_INACTIVE, color.ICON_STROKE_INACTIVE ]
        ]

        self._update_icon()
        self._update_name()
        self._update_state()

    def _strength_changed_cb(self, model, pspec):
        self._update_icon()

    def _name_changed_cb(self, model, pspec):
        self._update_name()

    def _state_changed_cb(self, model, pspec):
        self._update_state()

    def _activate_cb(self, icon):
        network_manager = hardwaremanager.get_network_manager()
        if network_manager:
            device = self._model.get_nm_device()
            network = self._model.get_nm_network()
            network_manager.set_active_device(device, network)

    def _update_name(self):
        self.props.tooltip = self._model.props.name

    def _update_icon(self):
        icon_name = canvasicon.get_icon_state(
                    _ICON_NAME, self._model.props.strength)
        if icon_name:
            self.props.icon_name = icon_name

    def _update_state(self):
        if self._model.props.state == accesspointmodel.STATE_CONNECTING:
            self.props.pulsing = True
        elif self._model.props.state == accesspointmodel.STATE_CONNECTED:
            self.props.pulsing = False
            self.props.fill_color = None
            self.props.stroke_color = None
        elif self._model.props.state == accesspointmodel.STATE_NOTCONNECTED:
            self.props.pulsing = False
            self.props.fill_color = color.ICON_FILL_INACTIVE
            self.props.stroke_color = color.ICON_STROKE_INACTIVE

class ActivityView(SnowflakeBox):
    def __init__(self, shell, menu_shell, model):
        SnowflakeBox.__init__(self)

        self._shell = shell
        self._model = model
        self._icons = {}

        icon = CanvasIcon(icon_name=model.get_icon_name(),
                          xo_color=model.get_color(), box_width=80)
        icon.connect('activated', self._clicked_cb)
        self.append(icon, hippo.PACK_FIXED)
        self.set_root(icon)

    def has_buddy_icon(self, name):
        return self._icons.has_key(name)

    def add_buddy_icon(self, name, icon):
        self._icons[name] = icon
        self.append(icon, hippo.PACK_FIXED)

    def remove_buddy_icon(self, name):
        icon = self._icons[name]
        self.remove(icon)
        del self._icons[name]

    def _clicked_cb(self, item):
        bundle_id = self._model.get_service().get_type()
        self._shell.join_activity(bundle_id, self._model.get_id())

class MeshBox(SpreadBox):
    def __init__(self, shell, menu_shell):
        SpreadBox.__init__(self, background_color=0xe2e2e2ff)

        self._shell = shell
        self._menu_shell = menu_shell
        self._model = shell.get_model().get_mesh()
        self._buddies = {}
        self._activities = {}
        self._access_points = {}
        self._buddy_to_activity = {}

        for buddy_model in self._model.get_buddies():
            self._add_alone_buddy(buddy_model)

        self._model.connect('buddy-added', self._buddy_added_cb)
        self._model.connect('buddy-removed', self._buddy_removed_cb)
        self._model.connect('buddy-moved', self._buddy_moved_cb)

        for activity_model in self._model.get_activities():
            self._add_activity(activity_model)

        self._model.connect('activity-added', self._activity_added_cb)
        self._model.connect('activity-removed', self._activity_removed_cb)

        for ap_model in self._model.get_access_points():
            self._add_access_point(ap_model)

        self._model.connect('access-point-added',
                            self._access_point_added_cb)
        self._model.connect('access-point-removed',
                            self._access_point_removed_cb)

    def _buddy_added_cb(self, model, buddy_model):
        self._add_alone_buddy(buddy_model)

    def _buddy_removed_cb(self, model, buddy_model):
        self._remove_buddy(buddy_model) 

    def _buddy_moved_cb(self, model, buddy_model, activity_model):
        self._move_buddy(buddy_model, activity_model)

    def _activity_added_cb(self, model, activity_model):
        self._add_activity(activity_model)

    def _activity_removed_cb(self, model, activity_model):
        self._remove_activity(activity_model) 

    def _access_point_added_cb(self, model, ap_model):
        self._add_access_point(ap_model)

    def _access_point_removed_cb(self, model, ap_model):
        self._remove_access_point(ap_model) 

    def _add_alone_buddy(self, buddy_model):
        icon = BuddyIcon(self._shell, self._menu_shell, buddy_model)
        self.add_item(icon)

        self._buddies[buddy_model.get_name()] = icon

    def _remove_alone_buddy(self, buddy_model):
        icon = self._buddies[buddy_model.get_name()]
        self.remove_item(icon)
        del self._buddies[buddy_model.get_name()]

    def _remove_buddy(self, buddy_model):
        name = buddy_model.get_name()
        if self._buddies.has_key(name):
            self._remove_alone_buddy(buddy_model)
        else:
            for activity in self._activities.values():
                if activity.has_buddy_icon(name):
                    activity.remove_buddy_icon(name)

    def _move_buddy(self, buddy_model, activity_model):
        name = buddy_model.get_name()

        self._remove_buddy(buddy_model)

        if activity_model == None:
            self._add_alone_buddy(buddy_model)
        else:
            activity = self._activities[activity_model.get_id()]

            icon = BuddyIcon(self._shell, self._menu_shell, buddy_model)
            activity.add_buddy_icon(buddy_model.get_name(), icon)

    def _add_activity(self, activity_model):
        icon = ActivityView(self._shell, self._menu_shell, activity_model)
        self.add_item(icon)

        self._activities[activity_model.get_id()] = icon

    def _remove_activity(self, activity_model):
        icon = self._activities[activity_model.get_id()]
        self.remove_item(icon)
        del self._activities[activity_model.get_id()]

    def _add_access_point(self, ap_model):
        icon = AccessPointView(ap_model)
        self.add_item(icon)

        self._access_points[ap_model.get_id()] = icon

    def _remove_access_point(self, ap_model):
        icon = self._access_points[ap_model.get_id()]
        self.remove_item(icon)
        del self._access_points[ap_model.get_id()]
