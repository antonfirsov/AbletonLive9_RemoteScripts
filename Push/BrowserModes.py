#Embedded file name: /Users/versonator/Hudson/live/Projects/AppLive/Resources/MIDI Remote Scripts/Push/BrowserModes.py
"""
Different mode objects that turn live into different browsing modes.
"""
import Live
DeviceType = Live.Device.DeviceType
from _Framework.Dependency import depends
from _Framework.Util import index_if
from _Framework.ModesComponent import Mode

def can_browse_for_object(obj):
    return obj != None and not isinstance(obj, (int, Live.Chain.Chain))


class BrowserHotswapMode(Mode):

    @depends(selection=None)
    def __init__(self, selection = None, application_view = None, *a, **k):
        super(BrowserHotswapMode, self).__init__(*a, **k)
        self._selection = selection
        self._application_view = application_view

    def can_hotswap(self):
        return can_browse_for_object(self._selection.hotswap_target) or can_browse_for_object(self._selection.selected_object) or can_browse_for_object(self._selection.selected_device)

    def enter_mode(self):
        self._ensure_valid_hotswap_target()
        if not self._application_view.browse_mode:
            self._application_view.toggle_browse()

    def leave_mode(self):
        if self._application_view.browse_mode:
            self._application_view.toggle_browse()

    def _ensure_valid_hotswap_target(self):
        if not can_browse_for_object(self._selection.hotswap_target):
            if not self._target_device_selected_object():
                self._target_selected_device()

    def _can_browse_for_object(self, obj):
        return obj != None and not isinstance(obj, (int, Live.Chain.Chain))

    def _make_object_the_hotswap_target(self, lom_object):
        self._selection.selected_object = lom_object

    def _target_device_selected_object(self):
        did_set_target = False
        lom_object = self._selection.selected_object
        if can_browse_for_object(lom_object):
            self._make_object_the_hotswap_target(lom_object)
            did_set_target = True
        return did_set_target

    def _target_selected_device(self):
        selected_device = self._selection.selected_device
        if can_browse_for_object(selected_device):
            self._make_object_the_hotswap_target(selected_device)


class BrowserAddEffectMode(Mode):
    insert_left = False

    @depends(selection=None)
    def __init__(self, selection = None, browser = None, insert_left = None, application_view = None, *a, **k):
        super(BrowserAddEffectMode, self).__init__(*a, **k)
        self._selection = selection
        self._browser = browser
        self._hotswap_was_enabled = False
        self._application_view = application_view
        self._track_to_add_effect = None
        self._selection_for_insert = None
        if insert_left is not None:
            self.insert_left = insert_left

    def enter_mode(self):
        self._track_to_add_effect = self._selection.selected_track
        self._selection_for_insert = self._do_get_selection_for_insert()
        self._track_to_add_effect.view.device_insert_mode = self.get_insert_mode()
        self._browser.filter_type = self.get_filter_type()
        self._hotswap_was_enabled = self._application_view.browse_mode
        if self._hotswap_was_enabled:
            self._application_view.toggle_browse()

    def leave_mode(self):
        disabled = Live.Track.DeviceInsertMode.default
        self._track_to_add_effect.view.device_insert_mode = disabled
        self._browser.filter_type = Live.Browser.FilterType.disabled
        if self._hotswap_was_enabled != self._application_view.browse_mode:
            self._application_view.toggle_browse()

    def get_insert_mode(self):
        return Live.Track.DeviceInsertMode.selected_left if self.insert_left else Live.Track.DeviceInsertMode.selected_right

    def get_selection_for_insert(self):
        """
        Device to use for reference of where to insert the device.
        """
        return self._selection_for_insert

    def _do_get_selection_for_insert(self):
        selected = self._selection.selected_object
        if isinstance(selected, Live.DrumPad.DrumPad) and selected.chains and selected.chains[0].devices:
            index = 0 if self.insert_left else -1
            selected = selected.chains[0].devices[index]
        elif not isinstance(selected, Live.Device.Device):
            selected = self._selection.selected_device
        return selected

    def get_filter_type(self):
        selected = self.get_selection_for_insert()
        chain = selected.canonical_parent if selected else self._selection.selected_track
        chain_len = len(chain.devices)
        index = index_if(lambda device: device == selected, chain.devices)
        is_drum_pad = isinstance(chain.canonical_parent, Live.DrumPad.DrumPad)
        midi_support = chain.has_midi_input
        if not is_drum_pad:
            supports_instrument = chain.has_midi_input and (chain.has_audio_output or isinstance(chain, Live.Track.Track))
            left = self.insert_left and (chain.devices[index - 1] if index > 0 else None)
            return filter_type_between(left, selected, midi_support, is_drum_pad, supports_instrument)
        else:
            right = chain.devices[index + 1] if index < chain_len - 1 else None
            return filter_type_between(selected, right, midi_support, is_drum_pad, supports_instrument)


def filter_type_between(left, right, supports_midi = False, is_drum_pad = False, supports_instrument = False):
    """
    Given 'left' and 'right' are two consecutive devices in a valid
    device chain, returns the appropriate browser filter type for valid
    devices fitting between them. Either 'left' or 'right' can be None
    to indicate chain boundaries.
    
    A valid device chain with MIDI support has the following structure:
    
        <midi effect>* <instrument> <audio effect>*
    
    A valid device chain without MIDI support has the following structure:
    
        <audio effect>*
    """
    Types = Live.Browser.FilterType
    if right and right.type in (DeviceType.instrument, DeviceType.midi_effect):
        return Types.midi_effect_hotswap
    if left and left.type in (DeviceType.instrument, DeviceType.audio_effect):
        return Types.audio_effect_hotswap
    if supports_midi:
        if supports_instrument:
            return Types.drum_pad_hotswap if is_drum_pad else Types.instrument_hotswap
        else:
            return Types.midi_effect_hotswap
    return Types.audio_effect_hotswap