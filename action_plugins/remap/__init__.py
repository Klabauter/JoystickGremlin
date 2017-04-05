# -*- coding: utf-8; -*-

# Copyright (C) 2015 - 2017 Lionel Ott
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from xml.etree import ElementTree

from .. import common
from gremlin.common import InputType
import gremlin.ui.common
import gremlin.ui.input_item


class RemapWidget(gremlin.ui.input_item.AbstractActionWidget):

    """Dialog which allows the selection of a vJoy output to use as
    as the remapping for the currently selected input.
    """

    # Mapping from types to display names
    type_to_name_map = {
        InputType.JoystickAxis: "Axis",
        InputType.JoystickButton: "Button",
        InputType.JoystickHat: "Hat",
        InputType.Keyboard: "Button",
    }
    name_to_type_map = {
        "Axis": InputType.JoystickAxis,
        "Button": InputType.JoystickButton,
        "Hat": InputType.JoystickHat
    }

    def __init__(self, action_data, parent=None):
        """Creates a new RemapWidget.

        :param action_data profile.InputItem data for this widget
        :param parent of this widget
        """
        devices = gremlin.joystick_handling.joystick_devices()
        self.vjoy_devices = [dev for dev in devices if dev.is_virtual]
        super().__init__(action_data, parent)
        assert(isinstance(action_data, Remap))

    def _create_ui(self):
        input_types = {
            InputType.Keyboard: [InputType.JoystickButton],
            InputType.JoystickAxis: [
                InputType.JoystickAxis,
                InputType.JoystickButton
            ],
            InputType.JoystickButton: [InputType.JoystickButton],
            InputType.JoystickHat: [InputType.JoystickHat]
        }
        self.vjoy_selector = gremlin.ui.common.VJoySelector(
            self.vjoy_devices,
            self.save_changes,
            input_types[self._get_input_type()]
        )
        self.main_layout.addWidget(self.vjoy_selector)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

    def _populate_ui(self):
        # If this is a new item, i.e. no vjoy device and vjoy input set
        # force the condition for buttons to trigger both on release and
        # press
        if self.action_data.vjoy_device_id is None and \
                self.action_data.vjoy_input_id is None and \
                self.action_data.get_input_type() == InputType.JoystickButton:
            self.action_data.condition.on_press = True
            self.action_data.condition.on_release = True

        # Get the appropriate vjoy device identifier
        vjoy_dev_id = 0
        if self.action_data.vjoy_device_id not in [0, None]:
            vjoy_dev_id = self.action_data.vjoy_device_id

        # If no valid input item is selected get the next unused one
        if self.action_data.vjoy_input_id in [0, None]:
            free_inputs = self._get_profile_root().list_unused_vjoy_inputs(
                self.vjoy_devices
            )
            input_type = self.type_to_name_map[self.action_data.input_type].lower()
            if vjoy_dev_id == 0:
                vjoy_dev_id = sorted(free_inputs.keys())[0]
            input_list = free_inputs[vjoy_dev_id][input_type]
            # If we have an unused item use it, otherwise use the first one
            if len(input_list) > 0:
                vjoy_input_id = input_list[0]
            else:
                vjoy_input_id = 1
        # If a valid input item is present use it
        else:
            vjoy_input_id = self.action_data.vjoy_input_id

        self.vjoy_selector.set_selection(
            self.action_data.input_type,
            vjoy_dev_id,
            vjoy_input_id
        )

    def save_changes(self):
        vjoy_data = self.vjoy_selector.get_selection()
        self.action_data.vjoy_device_id = vjoy_data["device_id"]
        self.action_data.vjoy_input_id = vjoy_data["input_id"]
        self.action_data.input_type = vjoy_data["input_type"]
        self.modified.emit()


class Remap(gremlin.base_classes.AbstractAction):

    """Action remapping physical joystick inputs to vJoy inputs."""

    icon = None
    name = "Remap"
    tag = "remap"
    widget = RemapWidget
    input_types = [
        InputType.JoystickAxis,
        InputType.JoystickButton,
        InputType.JoystickHat,
        InputType.Keyboard
    ]
    callback_params = ["vjoy"]

    def __init__(self, parent):
        super().__init__(parent)

        # FIXME: this used to be None instead of 1 does this change cause
        # bad side effects?
        self.vjoy_device_id = 1
        self.vjoy_input_id = 1
        self.input_type = self.parent.parent.input_type
        if self.input_type in [InputType.JoystickButton, InputType.Keyboard]:
            self.condition = gremlin.base_classes.ButtonCondition(True, True)

    def icon(self):
        input_string = "axis"
        if self.input_type == InputType.JoystickButton:
            input_string = "button"
        elif self.input_type == InputType.JoystickHat:
            input_string = "hat"
        return "action_plugins/remap/gfx/icon_{}_{:03d}.png".format(
                input_string,
                self.vjoy_input_id
            )

    def _parse_xml(self, node):
        if "axis" in node.attrib:
            self.input_type = InputType.JoystickAxis
            self.vjoy_input_id = int(node.get("axis"))
        elif "button" in node.attrib:
            self.input_type = InputType.JoystickButton
            self.vjoy_input_id = int(node.get("button"))
        elif "hat" in node.attrib:
            self.input_type = InputType.JoystickHat
            self.vjoy_input_id = int(node.get("hat"))
        elif "keyboard" in node.attrib:
            self.input_type = InputType.Keyboard
            self.vjoy_input_id = int(node.get("button"))
        else:
            raise gremlin.error.GremlinError(
                "Invalid remap type provided: {}".format(node.attrib)
            )

        self.vjoy_device_id = int(node.get("vjoy"))

    def _generate_xml(self):
        node = ElementTree.Element("remap")
        node.set("vjoy", str(self.vjoy_device_id))
        if self.input_type == InputType.Keyboard:
            node.set(
                common.input_type_to_tag(InputType.JoystickButton),
                str(self.vjoy_input_id)
            )
        else:
            node.set(
                common.input_type_to_tag(self.input_type),
                str(self.vjoy_input_id)
            )
        return node

    def _generate_code(self):
        return self._code_generation(
            "remap",
            {
                "entry": self
            }
        )

    def _is_valid(self):
        return True

version = 1
name = "remap"
create = Remap